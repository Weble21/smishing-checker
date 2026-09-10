import pytest

from smishing_api.risk import combine_analysis, requests_link_access
from smishing_api.schemas import TextAnalysisResult, UrlAnalysisResult, ReputationResult


def url(verdict):
    return UrlAnalysisResult(url="https://example.com/", verdict=verdict,
                             riskScore=0.8, reasons=[], reputation=ReputationResult(status="NOT_FOUND"))


@pytest.mark.parametrize("verdict,expected", [
    ("DANGEROUS", "HIGH"), ("SUSPICIOUS", "HIGH"),
    ("UNKNOWN", "LOW"), ("INVALID", "LOW"), ("NO_KNOWN_THREAT", "LOW"),
])
@pytest.mark.parametrize("score", [0.01, 0.99])
def test_url_verdict_controls_grade(verdict, expected, score):
    level, summary, _, _ = combine_analysis(
        TextAnalysisResult(label="NORMAL", riskScore=score), [url(verdict)],
        "인증번호를 입력하고 링크를 클릭하세요.",
    )
    assert level == expected
    if verdict == "SUSPICIOUS":
        assert "가능성이 높습니다" in summary
        assert "확인되었습니다" not in summary


@pytest.mark.parametrize("message,expected", [
    ("개인정보를 제출하세요.", "MEDIUM"),
    ("신용정보를\n보내주세요.", "MEDIUM"),
    ("신용카드정보를 입력하세요.", "MEDIUM"),
    ("계좌로 송금해 주세요.", "MEDIUM"),
    ("10만원 보내줘.", "MEDIUM"),
    ("인증번호를 알려주세요.", "MEDIUM"),
    ("[해외발신] 오늘까지 긴급 확인 바랍니다.", "LOW"),
    ("내일 배송 예정입니다.", "LOW"),
])
def test_text_only_caution_requires_sensitive_request(message, expected):
    assert combine_analysis(TextAnalysisResult(label="RISK", riskScore=0.99), [], message)[0] == expected


def test_safe_link_does_not_hide_a_risky_link():
    assert combine_analysis(TextAnalysisResult(label="NORMAL", riskScore=0.01),
                            [url("NO_KNOWN_THREAT"), url("SUSPICIOUS")],
                            "자세한 내용은 링크를 클릭하세요.")[0] == "MEDIUM"


@pytest.mark.parametrize("verdict", ["DANGEROUS", "SUSPICIOUS"])
def test_risky_link_without_sensitive_request_is_caution(verdict):
    level, summary, _, _ = combine_analysis(
        TextAnalysisResult(label="NORMAL", riskScore=0.01),
        [url(verdict)],
        "자세한 내용은 링크를 클릭하세요.",
    )
    assert level == "MEDIUM"
    assert "주의" in summary


def test_suspicious_link_without_access_request_stays_low():
    level, summary, reasons, _ = combine_analysis(
        TextAnalysisResult(label="NORMAL", riskScore=0.01),
        [url("SUSPICIOUS")],
        "회의 자료를 공유합니다.",
    )
    assert level == "LOW"
    assert "정상일 가능성이 높습니다" in summary
    assert any("직접 유도" in reason for reason in reasons)


@pytest.mark.parametrize("message", [
    "링크를 클릭해서 확인하세요.",
    "아래 주소로 접속 바랍니다.",
    "여기에서 확인하세요. https://example.com",
])
def test_detects_link_access_request(message):
    assert requests_link_access(message)


def test_link_mention_without_action_is_not_access_request():
    assert not requests_link_access("회의 자료 링크가 포함되어 있습니다.")
