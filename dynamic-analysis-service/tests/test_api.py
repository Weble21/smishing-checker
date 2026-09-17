from __future__ import annotations

from fastapi.testclient import TestClient

import app as app_module


client = TestClient(app_module.app)


def test_health_reports_fail_closed_state(monkeypatch):
    monkeypatch.setenv("DYNAMIC_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("DYNAMIC_ANALYSIS_EGRESS_READY", "false")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["analysisEnabled"] is False
    assert response.json()["egressPolicy"] == "controlled-proxy"


def test_analysis_requires_both_safety_gates(monkeypatch):
    monkeypatch.setenv("DYNAMIC_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("DYNAMIC_ANALYSIS_EGRESS_READY", "false")
    response = client.post("/analyze", json={"url": "https://example.com"})
    assert response.status_code == 503


def test_job_api_runs_and_returns_result(monkeypatch):
    async def fake_analyze(url, timeout):
        from schemas import DynamicAnalysisResponse
        return DynamicAnalysisResponse(
            status="COMPLETED", requestedUrl=url, finalUrl=url,
        )

    monkeypatch.setenv("DYNAMIC_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("DYNAMIC_ANALYSIS_EGRESS_READY", "true")
    monkeypatch.setattr(app_module, "analyze_url", fake_analyze)
    with TestClient(app_module.app) as job_client:
        created = job_client.post("/jobs", json={"url": "https://example.com"})
        assert created.status_code == 202
        job_id = created.json()["jobId"]
        for _ in range(20):
            result = job_client.get(f"/jobs/{job_id}")
            if result.json()["status"] == "COMPLETED":
                break
        assert result.status_code == 200
        assert result.json()["assessment"]["verdict"] == "NO_OBSERVED_THREAT"
