import json

import pytest

from smishing_api import url_model
from smishing_api.url_analysis import analyze_url
from smishing_api.risk import combine_analysis
from smishing_api.schemas import ReputationResult, TextAnalysisResult


@pytest.fixture
def isolated_model(monkeypatch, tmp_path):
    for name in ("_model", "_tokenizer", "_threshold", "_device", "_error"):
        monkeypatch.setattr(url_model, name, None)
    path = tmp_path / "model"
    path.mkdir()
    monkeypatch.setattr(url_model, "URL_MODEL_PATH", path)
    return path


@pytest.mark.parametrize("value,expected", [
    (" HXXPS://EXAMPLE[.]COM/Path?A=B ", "https://example.com/path?a=b"),
    ("example.com", "https://example.com"),
    ("hxxp://example.com/", "http://example.com/"),
])
def test_training_normalization(value, expected):
    assert url_model._model_document(value) == expected


def test_missing_model_is_visible_in_health(isolated_model):
    assert url_model.predict_url_risk("https://example.com") == (None, None)
    status = url_model.url_model_status()
    assert not status["loaded"]
    assert "MODEL_NOT_FOUND" in status["error"]


@pytest.mark.parametrize("threshold", [-1, 2, float("nan")])
def test_invalid_saved_threshold(isolated_model, threshold):
    (isolated_model / "config.json").write_text("{}", encoding="utf-8")
    (isolated_model.parent / "internal_test_metrics.json").write_text(
        json.dumps({"threshold": threshold}), encoding="utf-8"
    )
    assert not url_model.url_model_status()["loaded"]
    assert "INVALID_THRESHOLD" in url_model.url_model_status()["error"]


@pytest.mark.asyncio
@pytest.mark.parametrize("score,expected", [(0.32, "UNKNOWN"), (0.33, "SUSPICIOUS")])
async def test_transformer_threshold_flows_into_url_verdict(monkeypatch, score, expected):
    inputs = []
    def predict(url):
        inputs.append(url)
        return score, 0.32082128524780273
    monkeypatch.setattr("smishing_api.url_analysis.predict_url_risk", predict)
    result = await analyze_url("https://example.com", api_key="")
    assert inputs == ["https://example.com"]
    assert result.modelScore == score
    assert result.verdict == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("url,expected", [
    ("https://www.kbstar.com/", "NO_KNOWN_THREAT"),
    ("https://kbstar.com.evil.example/", "SUSPICIOUS"),
    ("https://open.kakao.com/o/example", "SUSPICIOUS"),
    ("http://www.kbstar.com/login", "SUSPICIOUS"),
])
async def test_whitelist_cancels_only_official_model_suspicion(monkeypatch, url, expected):
    monkeypatch.setattr("smishing_api.url_analysis.predict_url_risk", lambda url: (0.6114, 0.3208))
    result = await analyze_url(url, api_key="")
    assert result.modelScore == 0.6114
    assert result.verdict == expected
    if expected == "NO_KNOWN_THREAT":
        assert result.riskScore == 0.0
        assert any("화이트리스트" in reason for reason in result.reasons)
        text = TextAnalysisResult(label="NORMAL", riskScore=0.05)
        assert combine_analysis(text, [result], "[KB국민은행] 입금 알림입니다.")[0] == "LOW"
        assert combine_analysis(text, [result], "[KB국민은행] 인증번호를 입력하세요.")[0] == "LOW"


@pytest.mark.asyncio
@pytest.mark.parametrize("malicious,suspicious,expected", [
    (2, 0, "DANGEROUS"), (1, 0, "SUSPICIOUS"), (0, 1, "SUSPICIOUS"),
])
async def test_whitelist_preserves_security_engine_detections(monkeypatch, malicious, suspicious, expected):
    monkeypatch.setattr("smishing_api.url_analysis.predict_url_risk", lambda url: (0.6114, 0.3208))
    async def report(*args, **kwargs):
        return ReputationResult(status="FOUND", malicious=malicious, suspicious=suspicious)
    monkeypatch.setattr("smishing_api.url_analysis.get_virustotal_report", report)
    result = await analyze_url("https://www.kbstar.com/", api_key="")
    assert result.verdict == expected
