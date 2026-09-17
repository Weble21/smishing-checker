from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator


class DynamicAnalysisRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def validate_http_url(cls, value: str) -> str:
        parsed = urlsplit(value.strip())
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Only absolute HTTP(S) URLs are accepted")
        if parsed.username or parsed.password:
            raise ValueError("URLs containing credentials are not accepted")
        return value.strip()


class RedirectHop(BaseModel):
    url: str
    status: int = Field(ge=100, le=599)


class FormObservation(BaseModel):
    action: str
    method: str
    inputTypes: list[str] = Field(default_factory=list)
    sensitiveFields: list[str] = Field(default_factory=list)


class NetworkObservation(BaseModel):
    url: str
    method: str
    resourceType: str


class DownloadObservation(BaseModel):
    suggestedFilename: str


class DynamicAnalysisResponse(BaseModel):
    status: Literal["COMPLETED", "TIMED_OUT", "FAILED"]
    requestedUrl: str
    finalUrl: str | None = None
    title: str = ""
    visibleText: str = ""
    redirectChain: list[RedirectHop] = Field(default_factory=list)
    forms: list[FormObservation] = Field(default_factory=list)
    networkRequests: list[NetworkObservation] = Field(default_factory=list)
    downloads: list[DownloadObservation] = Field(default_factory=list)
    screenshotPngBase64: str | None = None
    truncated: bool = False
    errorCode: str | None = None


JobState = Literal["QUEUED", "RUNNING", "COMPLETED", "TIMED_OUT", "FAILED"]
DynamicVerdict = Literal[
    "DANGEROUS", "SUSPICIOUS", "NO_OBSERVED_THREAT", "INCONCLUSIVE",
]


class DynamicAssessment(BaseModel):
    verdict: DynamicVerdict
    reasons: list[str] = Field(default_factory=list)


class DynamicJobResponse(BaseModel):
    jobId: str
    status: JobState
    requestedUrl: str
    createdAt: str
    updatedAt: str
    result: DynamicAnalysisResponse | None = None
    assessment: DynamicAssessment | None = None
