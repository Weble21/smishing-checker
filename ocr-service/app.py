from __future__ import annotations

import os
import logging
import threading
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OCR_CACHE_DIR = Path(
    os.getenv("OCR_CACHE_DIR", str(PROJECT_ROOT / ".cache" / "ocr"))
)
os.environ.setdefault("PADDLE_HOME", str(OCR_CACHE_DIR / "paddle"))
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(OCR_CACHE_DIR / "paddlex"))

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from paddleocr import PaddleOCR
from pydantic import BaseModel


MAX_IMAGE_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
OCR_DEVICE = os.getenv("OCR_DEVICE", "cpu")

app = FastAPI(title="SafeLetter PaddleOCR", version="1.0.0")
logger = logging.getLogger(__name__)

_ocr: PaddleOCR | None = None
_ocr_lock = threading.RLock()


class OcrResponse(BaseModel):
    text: str
    confidence: float
    lineCount: int


def get_ocr() -> PaddleOCR:
    global _ocr

    if _ocr is not None:
        return _ocr

    with _ocr_lock:
        if _ocr is None:
            _ocr = PaddleOCR(
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="korean_PP-OCRv5_mobile_rec",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                text_rec_score_thresh=0.35,
                device=OCR_DEVICE,
                enable_mkldnn=False,
            )

    return _ocr


def extract_lines(image: np.ndarray) -> tuple[list[str], list[float]]:
    texts: list[str] = []
    scores: list[float] = []

    with _ocr_lock:
        results = get_ocr().predict(input=image)
        for result in results:
            payload = result.json
            if callable(payload):
                payload = payload()
            data = payload.get("res", payload)
            result_texts = data.get("rec_texts", [])
            result_scores = data.get("rec_scores", [])

            for index, raw_text in enumerate(result_texts):
                text = str(raw_text).strip()
                if not text:
                    continue

                score = (
                    float(result_scores[index])
                    if index < len(result_scores)
                    else 0.0
                )
                texts.append(text)
                scores.append(score)

    return texts, scores


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "modelLoaded": _ocr is not None,
        "device": OCR_DEVICE,
    }


@app.post("/ocr", response_model=OcrResponse)
async def recognize(image: UploadFile = File(...)) -> OcrResponse:
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="JPG or PNG only")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image")
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image exceeds 10MB")

    encoded = np.frombuffer(image_bytes, dtype=np.uint8)
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if decoded is None:
        raise HTTPException(status_code=422, detail="Invalid image")

    try:
        texts, scores = extract_lines(decoded)
    except Exception as exception:
        logger.exception("OCR inference failed")
        raise HTTPException(
            status_code=503,
            detail="OCR inference failed",
        ) from exception

    confidence = sum(scores) / len(scores) if scores else 0.0
    return OcrResponse(
        text="\n".join(texts),
        confidence=round(confidence, 4),
        lineCount=len(texts),
    )
