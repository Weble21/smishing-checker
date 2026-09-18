from __future__ import annotations

import os

import httpx

from .schemas import DynamicJobReference, DynamicJobStatus


def dynamic_analysis_enabled() -> bool:
    return (
        os.getenv("DYNAMIC_ANALYSIS_ENABLED", "false").lower() == "true"
        and bool(os.getenv("DYNAMIC_ANALYSIS_BASE_URL", "").strip())
    )


def _base_url() -> str:
    return os.getenv("DYNAMIC_ANALYSIS_BASE_URL", "").strip().rstrip("/")


def _timeout() -> float:
    try:
        return min(max(float(os.getenv("DYNAMIC_ANALYSIS_API_TIMEOUT_SECONDS", "3")), 1), 10)
    except ValueError:
        return 3


async def submit(url: str, *, client: httpx.AsyncClient | None = None) -> DynamicJobReference | None:
    if not dynamic_analysis_enabled():
        return None
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=_timeout())
    try:
        response = await client.post(f"{_base_url()}/jobs", json={"url": url})
        response.raise_for_status()
        payload = response.json()
        return DynamicJobReference.model_validate(payload)
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None
    finally:
        if owns_client:
            await client.aclose()


async def get_status(job_id: str, *, client: httpx.AsyncClient | None = None) -> DynamicJobStatus:
    if not dynamic_analysis_enabled():
        raise RuntimeError("Dynamic analysis is disabled")
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=_timeout())
    try:
        response = await client.get(
            f"{_base_url()}/jobs/{job_id}", params={"includeArtifacts": "false"},
        )
        response.raise_for_status()
        payload = response.json()
        assessment = payload.get("assessment") or {}
        result = payload.get("result") or {}
        verdict = assessment.get("verdict")
        reasons = assessment.get("reasons") or []
        evidence: list[str] = []
        if result.get("finalUrl"):
            evidence.append(f"최종 URL: {result['finalUrl']}")
        for hop in (result.get("redirectChain") or [])[:10]:
            evidence.append(f"이동 응답 {hop['status']}: {hop['url']}")
        for form in (result.get("forms") or [])[:10]:
            evidence.append(f"폼 {form['method']}: {form['action']} (입력 유형: {', '.join(form.get('inputTypes') or []) or '없음'})")
        requests = result.get("networkRequests") or []
        if requests:
            evidence.append(f"네트워크 요청: {len(requests)}건")
            for request in requests[:5]:
                evidence.append(f"{request['method']} {request['url']} ({request['resourceType']})")
        for download in (result.get("downloads") or [])[:10]:
            evidence.append(f"다운로드 시도: {download['suggestedFilename']}")
        risk_level = "HIGH" if verdict in {"DANGEROUS", "SUSPICIOUS"} else None
        summary = {
            "DANGEROUS": "동적 분석에서 실행 파일 다운로드 유도가 확인되었습니다.",
            "SUSPICIOUS": "동적 분석에서 민감정보 입력 폼이 확인되었습니다.",
            "NO_OBSERVED_THREAT": "동적 분석의 제한된 관찰 시간에는 강한 위험 행동이 확인되지 않았습니다.",
            "INCONCLUSIVE": "동적 분석을 완료하지 못했습니다.",
        }.get(verdict)
        if result.get("errorCode") == "BLOCKED_DESTINATION":
            summary = "웹페이지가 차단된 내부 주소로 이동하려 해 분석을 중단했습니다."
        return DynamicJobStatus(
            jobId=payload["jobId"], status=payload["status"],
            requestedUrl=payload["requestedUrl"], verdict=verdict,
            riskLevel=risk_level, summary=summary, reasons=reasons,
            evidence=evidence,
        )
    finally:
        if owns_client:
            await client.aclose()
