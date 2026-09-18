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
@pytest.mark.parametrize("status", ["TIMED_OUT", "FAILED"])
async def test_incomplete_analysis_is_never_safe(monkeypatch, status):
    monkeypatch.setenv("DYNAMIC_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("DYNAMIC_ANALYSIS_BASE_URL", "http://dynamic-analysis:8081")

    def handler(request):
        return httpx.Response(200, json={
            "jobId": "c" * 32, "status": status,
            "requestedUrl": "https://example.com/",
            "assessment": {"verdict": "INCONCLUSIVE", "reasons": ["동적 분석을 완료하지 못했습니다."]},
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await get_status("c" * 32, client=client)
    assert result.verdict == "INCONCLUSIVE"
    assert result.riskLevel is None
    assert result.evidence == []


@pytest.mark.asyncio
async def test_status_exposes_redacted_observations(monkeypatch):
    monkeypatch.setenv("DYNAMIC_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("DYNAMIC_ANALYSIS_BASE_URL", "http://dynamic-analysis:8081")

    def handler(request):
        return httpx.Response(200, json={
            "jobId": "d" * 32, "status": "COMPLETED",
            "requestedUrl": "https://example.com/",
            "assessment": {"verdict": "DANGEROUS", "reasons": ["다운로드 시도"]},
            "result": {
                "finalUrl": "https://example.com/final",
                "redirectChain": [{"status": 302, "url": "https://example.com/redirect"}],
                "forms": [{"method": "POST", "action": "https://example.com/submit", "inputTypes": ["password"]}],
                "networkRequests": [{"method": "GET", "url": "https://example.com/final", "resourceType": "document"}],
                "downloads": [{"suggestedFilename": "update.apk"}],
            },
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await get_status("d" * 32, client=client)
    assert result.riskLevel == "HIGH"
    assert any("최종 URL" in item for item in result.evidence)
    assert any("이동 응답 302" in item for item in result.evidence)
    assert any("폼 POST" in item for item in result.evidence)
    assert any("네트워크 요청: 1건" in item for item in result.evidence)
    assert any("다운로드 시도: update.apk" in item for item in result.evidence)


@pytest.mark.asyncio
async def test_blocked_redirect_is_inconclusive_with_specific_summary(monkeypatch):
    monkeypatch.setenv("DYNAMIC_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("DYNAMIC_ANALYSIS_BASE_URL", "http://dynamic-analysis:8081")

    def handler(request):
        return httpx.Response(200, json={
            "jobId": "e" * 32, "status": "FAILED",
            "requestedUrl": "https://example.com/redirect",
            "assessment": {"verdict": "INCONCLUSIVE", "reasons": ["웹페이지가 차단된 내부 주소로 이동하려 했습니다."]},
            "result": {
                "status": "FAILED", "requestedUrl": "https://example.com/redirect",
                "finalUrl": "http://127.0.0.1/", "errorCode": "BLOCKED_DESTINATION",
                "redirectChain": [{"status": 302, "url": "https://example.com/redirect"}],
            },
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await get_status("e" * 32, client=client)
    assert result.riskLevel is None
    assert "내부 주소" in result.summary
    assert any("최종 URL: http://127.0.0.1/" in item for item in result.evidence)


@pytest.mark.asyncio
async def test_submit_failure_does_not_break_static_analysis(monkeypatch):
    monkeypatch.setenv("DYNAMIC_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("DYNAMIC_ANALYSIS_BASE_URL", "http://dynamic-analysis:8081")

    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await submit("https://example.com/", client=client) is None
