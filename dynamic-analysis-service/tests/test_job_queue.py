from __future__ import annotations

import asyncio

import pytest

from job_queue import JobQueue
from assessment import assess
from schemas import (
    DownloadObservation,
    DynamicAnalysisResponse,
    FormObservation,
)


def completed(url: str, *, downloads=None, forms=None):
    return DynamicAnalysisResponse(
        status="COMPLETED", requestedUrl=url, finalUrl=url,
        downloads=downloads or [], forms=forms or [],
    )


def test_queue_runs_one_job_and_deduplicates_active_url():
    async def exercise():
        release = asyncio.Event()
        calls = []

        async def runner(url, timeout):
            calls.append(url)
            await release.wait()
            return completed(url)

        queue = JobQueue(runner, 5)
        queue.start()
        first = await queue.submit("https://example.com/path?token=one")
        second = await queue.submit("https://example.com/path?token=one")
        assert first.jobId == second.jobId
        release.set()
        await asyncio.wait_for(queue._queue.join(), 1)
        result = queue.get(first.jobId)
        assert result.status == "COMPLETED"
        assert result.requestedUrl == "https://example.com/path?token=REDACTED"
        assert result.assessment.verdict == "NO_OBSERVED_THREAT"
        assert calls == ["https://example.com/path?token=one"]
        await queue.stop()

    asyncio.run(exercise())


@pytest.mark.parametrize("result,verdict", [
    (completed("https://x.example", downloads=[
        DownloadObservation(suggestedFilename="update.apk"),
    ]), "DANGEROUS"),
    (completed("https://x.example", forms=[FormObservation(
        action="https://collect.example/submit", method="POST",
        inputTypes=["password"], sensitiveFields=["password"],
    )]), "SUSPICIOUS"),
])
def test_queue_assesses_observed_evidence(result, verdict):
    async def exercise():
        async def runner(url, timeout):
            return result
        queue = JobQueue(runner, 5)
        queue.start()
        submitted = await queue.submit(result.requestedUrl)
        await asyncio.wait_for(queue._queue.join(), 1)
        assert queue.get(submitted.jobId).assessment.verdict == verdict
        await queue.stop()
    asyncio.run(exercise())


def test_queue_returns_explicit_failure():
    async def exercise():
        async def runner(url, timeout):
            raise RuntimeError("boom")
        queue = JobQueue(runner, 5)
        queue.start()
        submitted = await queue.submit("https://example.com")
        await asyncio.wait_for(queue._queue.join(), 1)
        result = queue.get(submitted.jobId)
        assert result.status == "FAILED"
        assert result.assessment.verdict == "INCONCLUSIVE"
        await queue.stop()
    asyncio.run(exercise())


def test_blocked_destination_is_inconclusive_with_reason():
    result = DynamicAnalysisResponse(
        status="FAILED", requestedUrl="https://example.com/redirect",
        finalUrl="http://127.0.0.1/", errorCode="BLOCKED_DESTINATION",
    )
    assessment = assess(result)
    assert assessment.verdict == "INCONCLUSIVE"
    assert "차단된 내부 주소" in assessment.reasons[0]
