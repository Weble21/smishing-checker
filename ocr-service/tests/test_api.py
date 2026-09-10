from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

import app as app_module
from smishing_api.schemas import (
    OcrResponse,
    ReputationResult,
    TextAnalysisResult,
    UrlAnalysisResult,
)


client = TestClient(app_module.app)
ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@pytest.mark.parametrize("endpoint", ["/ocr", "/analyze"])
@pytest.mark.parametrize("error, status, detail", [
    (ValueError("bad image"), 422, "Invalid image"),
    (RuntimeError("unavailable"), 503, "OCR inference failed"),
])
def test_ocr_errors_keep_status_and_detail(monkeypatch, endpoint, error, status, detail):
    def fail_ocr(image):
        raise error

    monkeypatch.setattr(app_module, "extract_text", fail_ocr)
    response = client.post(
        endpoint, files={"image": ("message.png", ONE_PIXEL_PNG, "image/png")},
    )
    assert response.status_code == status
    assert response.json() == {"detail": detail}


def test_low_confidence_ocr_is_available_but_not_used_for_analysis(monkeypatch):
    monkeypatch.setattr(app_module, "extract_text", lambda image: OcrResponse(
        text="unclear", confidence=0, lineCount=1,
    ))
    files = {"image": ("message.png", ONE_PIXEL_PNG, "image/png")}
    assert client.post("/ocr", files=files).json()["confidence"] == 0
    response = client.post("/analyze", files=files)
    assert response.status_code == 422
    assert response.json()["detail"] == "OCR text is empty or confidence is too low"


@pytest.mark.parametrize("endpoint", ["/url/analyze", "/analyze"])
def test_url_results_preserve_order_and_remove_duplicates(monkeypatch, endpoint):
    message = "https://first.invalid https://second.invalid https://first.invalid"
    monkeypatch.setattr(app_module, "extract_text", lambda image: OcrResponse(
        text=message, confidence=0.99, lineCount=1,
    ))
    monkeypatch.setattr(app_module, "predict_text", lambda text: TextAnalysisResult(
        label="NORMAL", riskScore=0.03,
    ))

    async def analyze_url(url, *, client):
        return UrlAnalysisResult(
            url=url, verdict="UNKNOWN", riskScore=0,
            reputation=ReputationResult(status="NOT_CONFIGURED"),
        )

    monkeypatch.setattr(app_module, "analyze_url", analyze_url)
    if endpoint == "/url/analyze":
        response = client.post(endpoint, json={"text": message})
        assert response.json()["urlCount"] == 2
        results = response.json()["results"]
    else:
        response = client.post(
            endpoint, files={"image": ("message.png", ONE_PIXEL_PNG, "image/png")},
        )
        results = response.json()["urlAnalysis"]
    assert response.status_code == 200
    assert [result["url"] for result in results] == [
        "https://first.invalid", "https://second.invalid",
    ]


def test_url_endpoint_without_url() -> None:
    response = client.post("/url/analyze", json={"text": "오늘 저녁 같이 먹자."})
    assert response.status_code == 200
    assert response.json() == {"urlCount": 0, "results": []}


def test_integrated_image_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module,
        "extract_text",
        lambda image: OcrResponse(
            text="오늘 6시에 만나자.", confidence=0.99, lineCount=1
        ),
    )
    monkeypatch.setattr(
        app_module,
        "predict_text",
        lambda text: TextAnalysisResult(label="NORMAL", riskScore=0.03),
    )
    response = client.post(
        "/analyze",
        files={"image": ("message.png", ONE_PIXEL_PNG, "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["riskLevel"] == "LOW"
    assert response.json()["textAnalysis"]["label"] == "NORMAL"


def test_integrated_endpoint_rejects_wrong_content_type() -> None:
    response = client.post(
        "/analyze",
        files={"image": ("message.txt", b"not image", "text/plain")},
    )
    assert response.status_code == 415


def test_health_exposes_all_compose_readiness_fields(monkeypatch) -> None:
    for name in ("ocr_status", "model_status", "url_model_status"):
        monkeypatch.setattr(app_module, name, lambda: {"loaded": True})
    response = client.get("/health")
    assert response.status_code == 200
    health = response.json()
    assert all(health[name]["loaded"] for name in ("ocr", "textModel", "urlModel"))


def test_integrated_endpoint_passes_ocr_text_to_risk_policy(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "extract_text", lambda image: OcrResponse(
        text="인증번호를 알려주세요.", confidence=0.99, lineCount=1,
    ))
    monkeypatch.setattr(app_module, "predict_text", lambda text: TextAnalysisResult(
        label="NORMAL", riskScore=0.03,
    ))
    response = client.post(
        "/analyze", files={"image": ("message.png", ONE_PIXEL_PNG, "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["riskLevel"] == "MEDIUM"
