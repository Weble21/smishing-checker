from __future__ import annotations

import pytest
from pydantic import ValidationError

from analyzer import redact_url
from schemas import DynamicAnalysisRequest, DynamicAnalysisResponse


@pytest.mark.parametrize("url", [
    "https://example.com/path", "http://example.com/",
])
def test_accepts_absolute_http_urls(url):
    assert DynamicAnalysisRequest(url=url).url == url


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "javascript:alert(1)", "//example.com",
    "https://user:password@example.com/", "not-a-url",
])
def test_rejects_non_http_or_credential_urls(url):
    with pytest.raises(ValidationError):
        DynamicAnalysisRequest(url=url)


def test_redacts_query_values_and_fragment():
    assert redact_url("https://example.com/a?token=secret&empty=#part") == (
        "https://example.com/a?token=REDACTED&empty=REDACTED"
    )


def test_failed_result_never_implies_safety():
    result = DynamicAnalysisResponse(
        status="FAILED", requestedUrl="https://example.com", errorCode="ANALYSIS_FAILED",
    )
    assert result.status == "FAILED"
    assert result.finalUrl is None

