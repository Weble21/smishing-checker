from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from .config import OCR_DEVICE, PROJECT_DIR
from .schemas import OcrResponse


OCR_CACHE_DIR = Path(
    os.getenv("OCR_CACHE_DIR", str(PROJECT_DIR / ".cache" / "ocr"))
)
os.environ.setdefault("PADDLE_HOME", str(OCR_CACHE_DIR / "paddle"))
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(OCR_CACHE_DIR / "paddlex"))

_ocr: Any | None = None
_ocr_lock = threading.RLock()


def ocr_status() -> dict[str, object]:
    return {"loaded": _ocr is not None, "device": OCR_DEVICE}


def get_ocr() -> Any:
    global _ocr
    if _ocr is not None:
        return _ocr
    with _ocr_lock:
        if _ocr is None:
            # On Windows PaddleX imports ModelScope, which imports PyTorch.
            # Loading PyTorch before Paddle avoids conflicting DLL resolution.
            import torch  # noqa: F401
            from paddleocr import PaddleOCR

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


def extract_text(image_bytes: bytes) -> OcrResponse:
    import cv2
    import numpy as np

    encoded = np.frombuffer(image_bytes, dtype=np.uint8)
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if decoded is None:
        raise ValueError("Invalid image")

    texts: list[str] = []
    scores: list[float] = []
    with _ocr_lock:
        results = get_ocr().predict(input=decoded)
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

    confidence = sum(scores) / len(scores) if scores else 0.0
    return OcrResponse(
        text="\n".join(texts),
        confidence=round(confidence, 4),
        lineCount=len(texts),
    )
