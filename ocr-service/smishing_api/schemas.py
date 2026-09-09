from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["HIGH", "MEDIUM", "LOW"]
UrlVerdict = Literal[
    "DANGEROUS",
    "SUSPICIOUS",
    "NO_KNOWN_THREAT",
    "UNKNOWN",
    "INVALID",
]


class UrlAnalyzeRequest(BaseModel):
    text: str = Field(max_length=100_000)


class ReputationResult(BaseModel):
    status: str
    malicious: int = 0
    suspicious: int = 0


class UrlAnalysisResult(BaseModel):
    url: str
    hostname: str = ""
    verdict: UrlVerdict
    riskScore: float = Field(ge=0, le=1)
    modelScore: float | None = Field(default=None, ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)
    reputation: ReputationResult


class UrlAnalyzeResponse(BaseModel):
    urlCount: int
    results: list[UrlAnalysisResult]


class TextAnalysisResult(BaseModel):
    label: Literal["NORMAL", "RISK"]
    riskScore: float = Field(ge=0, le=1)


class OcrResponse(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    lineCount: int = Field(ge=0)


class IntegratedAnalysisResponse(BaseModel):
    ocrText: str
    textAnalysis: TextAnalysisResult
    urlAnalysis: list[UrlAnalysisResult]
    riskLevel: RiskLevel
    summary: str
    reasons: list[str]
    actions: list[str]
