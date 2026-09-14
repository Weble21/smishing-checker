"""Optional instruction-model review; KoELECTRA remains a binary classifier."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .domain_registry import lookup_domain, brand_is_relevant
from .schemas import TextAnalysisResult, UrlAnalysisResult

logger = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).with_name("prompts") / "smishing_review.txt"
RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
Analysis = tuple[str, str, list[str], list[str]]
CAUTION_ACTIONS = [
    "문자 속 링크 대신 기존에 사용하던 공식 앱이나 대표번호로 확인하세요.",
    "확인 전에는 개인정보·인증번호·지갑 복구문구를 입력하거나 송금하지 마세요.",
]


class ContextReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    riskLevel: Literal["LOW", "MEDIUM", "HIGH"]
    summary: str = Field(min_length=1, max_length=500)
    reasons: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(min_length=1, max_length=8)


async def review_context(
    message: str, text: TextAnalysisResult, urls: list[UrlAnalysisResult],
    *, client: httpx.AsyncClient,
) -> ContextReview:
    evidence = []
    for url in urls:
        match = lookup_domain(url.url)
        evidence.append({
            "url": url.url,
            "registryMatch": match,
            "brandRelevant": brand_is_relevant(message, match),
        })
    schema = ContextReview.model_json_schema()
    payload = {
        "model": os.environ["CONTEXT_LLM_MODEL"],
        "stream": False,
        "format": schema,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8")
             + "\nJSON Schema:\n" + json.dumps(schema, ensure_ascii=False)},
            {"role": "user", "content": json.dumps({
                "message": message,
                "textAnalysis": text.model_dump(),
                "urlAnalysis": [url.model_dump() for url in urls],
                "domainEvidence": evidence,
            }, ensure_ascii=False)},
        ],
    }
    base = os.getenv("CONTEXT_LLM_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    response = await client.post(base + "/api/chat", json=payload)
    response.raise_for_status()
    body = response.json()
    if body.get("done") is not True or body.get("done_reason") == "length":
        raise ValueError("Incomplete context review")
    return ContextReview.model_validate_json(body["message"]["content"])


async def apply_context_review(
    baseline: Analysis, message: str, text: TextAnalysisResult,
    urls: list[UrlAnalysisResult],
) -> Analysis:
    if not os.getenv("CONTEXT_LLM_MODEL", "").strip():
        return baseline
    level, summary, reasons, actions = baseline
    try:
        timeout = float(os.getenv("CONTEXT_LLM_TIMEOUT_SECONDS", "30"))
        async with asyncio.timeout(timeout):
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                review = await review_context(message, text, urls, client=client)
    except (httpx.HTTPError, ValueError, KeyError, TypeError, OSError, TimeoutError):
        # Do not log SMS contents or return LOW as if the configured review succeeded.
        logger.warning("Context review unavailable or invalid")
        if level == "LOW":
            return ("MEDIUM", "문맥 분석을 완료하지 못해 추가 확인이 필요합니다.",
                    [*reasons, "설정된 LLM 문맥 분석이 실패했습니다."], CAUTION_ACTIONS.copy())
        return level, summary, [*reasons, "LLM 문맥 분석 실패로 기존 위험 판정을 유지했습니다."], actions
    # An instruction model cannot remove an existing warning.
    if RANK[review.riskLevel] > RANK[level]:
        return (review.riskLevel, review.summary,
                [*reasons, *[f"문맥 분석: {reason}" for reason in review.reasons]],
                CAUTION_ACTIONS.copy())
    return level, summary, [*reasons, "LLM 문맥 검토 후 기존 위험 등급을 유지했습니다."], actions
