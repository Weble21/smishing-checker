from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Awaitable, Callable
from uuid import uuid4

from analyzer import redact_url
from assessment import assess
from schemas import DynamicAnalysisResponse, DynamicJobResponse


Runner = Callable[[str, float], Awaitable[DynamicAnalysisResponse]]


@dataclass
class _Job:
    job_id: str
    url: str
    status: str
    created_at: datetime
    updated_at: datetime
    result: DynamicAnalysisResponse | None = None


class JobQueue:
    def __init__(
        self,
        runner: Runner,
        timeout_seconds: float,
        *,
        capacity: int = 100,
        retained_jobs: int = 200,
        retention_minutes: int = 30,
    ) -> None:
        self._runner = runner
        self._timeout_seconds = timeout_seconds
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=capacity)
        self._jobs: OrderedDict[str, _Job] = OrderedDict()
        self._active_by_url: dict[str, str] = {}
        self._retained_jobs = retained_jobs
        self._retention = timedelta(minutes=retention_minutes)
        self._worker: asyncio.Task | None = None

    def start(self) -> None:
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._work())

    async def stop(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            await asyncio.gather(self._worker, return_exceptions=True)
            self._worker = None

    async def submit(self, url: str) -> DynamicJobResponse:
        self._purge()
        dedupe_key = url
        existing_id = self._active_by_url.get(dedupe_key)
        if existing_id and existing_id in self._jobs:
            return self._response(self._jobs[existing_id])
        if self._queue.full():
            raise asyncio.QueueFull
        now = datetime.now(UTC)
        job = _Job(uuid4().hex, url, "QUEUED", now, now)
        self._jobs[job.job_id] = job
        self._active_by_url[dedupe_key] = job.job_id
        await self._queue.put(job.job_id)
        return self._response(job)

    def get(self, job_id: str) -> DynamicJobResponse | None:
        self._purge()
        job = self._jobs.get(job_id)
        return None if job is None else self._response(job)

    async def _work(self) -> None:
        while True:
            job_id = await self._queue.get()
            job = self._jobs.get(job_id)
            try:
                if job is None:
                    continue
                job.status = "RUNNING"
                job.updated_at = datetime.now(UTC)
                try:
                    job.result = await asyncio.wait_for(
                        self._runner(job.url, self._timeout_seconds),
                        timeout=self._timeout_seconds + 5,
                    )
                    job.status = job.result.status
                except TimeoutError:
                    job.status = "TIMED_OUT"
                    job.result = DynamicAnalysisResponse(
                        status="TIMED_OUT", requestedUrl=redact_url(job.url),
                        errorCode="ANALYSIS_TIMEOUT",
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    job.status = "FAILED"
                    job.result = DynamicAnalysisResponse(
                        status="FAILED", requestedUrl=redact_url(job.url),
                        errorCode="ANALYSIS_FAILED",
                    )
                job.updated_at = datetime.now(UTC)
                self._active_by_url.pop(job.url, None)
            finally:
                self._queue.task_done()

    def _purge(self) -> None:
        cutoff = datetime.now(UTC) - self._retention
        removable = [job_id for job_id, job in self._jobs.items()
                     if job.status not in {"QUEUED", "RUNNING"} and job.updated_at < cutoff]
        while len(self._jobs) - len(removable) > self._retained_jobs:
            candidate = next((job_id for job_id, job in self._jobs.items()
                              if job.status not in {"QUEUED", "RUNNING"}
                              and job_id not in removable), None)
            if candidate is None:
                break
            removable.append(candidate)
        for job_id in removable:
            self._jobs.pop(job_id, None)

    @staticmethod
    def _response(job: _Job) -> DynamicJobResponse:
        return DynamicJobResponse(
            jobId=job.job_id,
            status=job.status,
            requestedUrl=redact_url(job.url),
            createdAt=job.created_at.isoformat(),
            updatedAt=job.updated_at.isoformat(),
            result=job.result,
            assessment=None if job.result is None else assess(job.result),
        )
