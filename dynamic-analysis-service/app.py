from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from analyzer import analyze_url, redact_url
from job_queue import JobQueue
from schemas import DynamicAnalysisRequest, DynamicAnalysisResponse, DynamicJobResponse


job_queue: JobQueue | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global job_queue
    job_queue = JobQueue(analyze_url, timeout_seconds())
    job_queue.start()
    try:
        yield
    finally:
        await job_queue.stop()
        job_queue = None


app = FastAPI(
    title="SafeLetter Dynamic URL Analysis", version="0.2.0", lifespan=lifespan,
)
analysis_slot = asyncio.Semaphore(1)


def enabled() -> bool:
    return (
        os.getenv("DYNAMIC_ANALYSIS_ENABLED", "false").lower() == "true"
        and os.getenv("DYNAMIC_ANALYSIS_EGRESS_READY", "false").lower() == "true"
    )


def timeout_seconds() -> float:
    value = float(os.getenv("DYNAMIC_ANALYSIS_TIMEOUT_SECONDS", "15"))
    return min(max(value, 5), 30)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "analysisEnabled": enabled(),
        "egressPolicy": "controlled-proxy",
    }


@app.post("/analyze", response_model=DynamicAnalysisResponse)
async def analyze(request: DynamicAnalysisRequest) -> DynamicAnalysisResponse:
    if not enabled():
        raise HTTPException(
            status_code=503,
            detail="Dynamic analysis is disabled until controlled egress is configured",
        )
    try:
        timeout = timeout_seconds()
        async with analysis_slot:
            return await asyncio.wait_for(
                analyze_url(request.url, timeout), timeout=timeout + 5,
            )
    except TimeoutError:
        return DynamicAnalysisResponse(
            status="TIMED_OUT",
            requestedUrl=redact_url(request.url),
            errorCode="ANALYSIS_TIMEOUT",
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        return DynamicAnalysisResponse(
            status="FAILED",
            requestedUrl=redact_url(request.url),
            errorCode="ANALYSIS_FAILED",
        )


@app.post(
    "/jobs", response_model=DynamicJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_job(request: DynamicAnalysisRequest) -> DynamicJobResponse:
    if not enabled() or job_queue is None:
        raise HTTPException(
            status_code=503,
            detail="Dynamic analysis is disabled or not ready",
        )
    try:
        return await job_queue.submit(request.url)
    except asyncio.QueueFull as exception:
        raise HTTPException(status_code=429, detail="Analysis queue is full") from exception


@app.get("/jobs/{job_id}", response_model=DynamicJobResponse)
def get_job(job_id: str, includeArtifacts: bool = True) -> DynamicJobResponse:
    if job_queue is None:
        raise HTTPException(status_code=503, detail="Dynamic analysis is not ready")
    job = job_queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job was not found")
    if not includeArtifacts and job.result is not None:
        job = job.model_copy(update={"result": job.result.model_copy(update={
            "visibleText": "", "screenshotPngBase64": None,
        })})
    return job
