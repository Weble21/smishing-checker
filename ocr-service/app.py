from __future__ import annotations

import asyncio
import logging

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from smishing_api.config import (
    ALLOWED_CONTENT_TYPES,
    MAX_IMAGE_SIZE,
    OCR_MIN_CONFIDENCE,
    VT_TIMEOUT_SECONDS,
)
from smishing_api.ocr import extract_text, ocr_status
from smishing_api.risk import combine_analysis
from smishing_api.schemas import (
    IntegratedAnalysisResponse,
    OcrResponse,
    UrlAnalysisResult,
    UrlAnalyzeRequest,
    UrlAnalyzeResponse,
)
from smishing_api.text_model import model_status, predict_text
from smishing_api.url_analysis import analyze_url, extract_urls
from smishing_api.url_model import url_model_status


app = FastAPI(title="SafeLetter Smishing Analysis", version="2.0.0")
logger = logging.getLogger(__name__)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "ocr": ocr_status(),
        "textModel": model_status(),
        "urlModel": url_model_status(),
    }


@app.post("/ocr", response_model=OcrResponse)
async def recognize(image: UploadFile = File(...)) -> OcrResponse:
    return await _recognize_image(image)


@app.post("/url/analyze", response_model=UrlAnalyzeResponse)
async def analyze_urls(request: UrlAnalyzeRequest) -> UrlAnalyzeResponse:
    results = await _analyze_text_urls(request.text)
    return UrlAnalyzeResponse(urlCount=len(results), results=results)


@app.post("/analyze", response_model=IntegratedAnalysisResponse)
async def analyze_image(
    image: UploadFile = File(...),
) -> IntegratedAnalysisResponse:
    ocr_result = await _recognize_image(image)

    if not ocr_result.text or ocr_result.confidence < OCR_MIN_CONFIDENCE:
        raise HTTPException(
            status_code=422,
            detail="OCR text is empty or confidence is too low",
        )

    try:
        text_result = await run_in_threadpool(predict_text, ocr_result.text)
    except Exception as exception:
        logger.exception("Text model inference failed")
        raise HTTPException(
            status_code=503,
            detail="Text model inference failed",
        ) from exception

    url_results = await _analyze_text_urls(ocr_result.text)

    risk_level, summary, reasons, actions = combine_analysis(
        text_result,
        url_results,
        ocr_result.text,
    )
    return IntegratedAnalysisResponse(
        ocrText=ocr_result.text,
        textAnalysis=text_result,
        urlAnalysis=url_results,
        riskLevel=risk_level,
        summary=summary,
        reasons=reasons,
        actions=actions,
    )


async def _recognize_image(image: UploadFile) -> OcrResponse:
    image_bytes = await _read_valid_image(image)
    try:
        return await run_in_threadpool(extract_text, image_bytes)
    except ValueError as exception:
        raise HTTPException(status_code=422, detail="Invalid image") from exception
    except Exception as exception:
        logger.exception("OCR inference failed")
        raise HTTPException(status_code=503, detail="OCR inference failed") from exception


async def _analyze_text_urls(text: str) -> list[UrlAnalysisResult]:
    candidates = extract_urls(text)
    if not candidates:
        return []
    async with httpx.AsyncClient(
        timeout=VT_TIMEOUT_SECONDS,
        follow_redirects=False,
    ) as client:
        return list(await asyncio.gather(
            *(analyze_url(url, client=client) for url in candidates)
        ))


async def _read_valid_image(image: UploadFile) -> bytes:
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="JPG or PNG only")
    image_bytes = await image.read(MAX_IMAGE_SIZE + 1)
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image")
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image exceeds 10MB")
    return image_bytes
