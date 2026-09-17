from __future__ import annotations

import httpx
import pytest

from smishing_api.dynamic_analysis import get_status, submit


@pytest.mark.asyncio
async def test_submit_returns_job_reference(monkeypatch):
    monkeypatch.setenv("DYNAMIC_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("DYNAMIC_ANALYSIS_BASE_URL", "http://dynamic-analysis:8081")

    async def handler(request):
        assert request.url.path == "/jobs"
        return httpx.Response(202, json={
            "jobId": "a" * 32, "status": "QUEUED",
            "requestedUrl": "https://example.com/",
            "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z",
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await submit("https://example.com/", client=client)
    assert result.jobId == "a" * 32


@pytest.mark.asyncio
@pytest.mark.parametrize("verdict,level", [
    ("DANGEROUS", "HIGH"), ("SUSPICIOUS", "HIGH"),
    ("NO_OBSERVED_THREAT", None), ("INCONCLUSIVE", None),
])
async def test_status_only_escalates_observed_risk(monkeypatch, verdict, level):
    monkeypatch.setenv("DYNAMIC_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("DYNAMIC_ANALYSIS_BASE_URL", "http://dynamic-analysis:8081")

    async def handler(request):
        assert request.url.params["includeArtifacts"] == "false"
        return httpx.Response(200, json={
            "jobId": "b" * 32, "status": "COMPLETED",
            "requestedUrl": "https://example.com/",
            "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:01Z",
            "assessment": {"verdict": verdict, "reasons": ["관찰 근거"]},
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await get_status("b" * 32, client=client)
    assert result.riskLevel == level
    assert result.reasons == ["관찰 근거"]


@pytest.mark.asyncio
async def test_submit_failure_does_not_break_static_analysis(monkeypatch):
    monkeypatch.setenv("DYNAMIC_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("DYNAMIC_ANALYSIS_BASE_URL", "http://dynamic-analysis:8081")

    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await submit("https://example.com/", client=client) is None
