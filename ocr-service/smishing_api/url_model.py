from __future__ import annotations

import json
import math
import re
import threading
from typing import Any

from .config import URL_MODEL_PATH


_lock = threading.RLock()
_model: Any = None
_tokenizer: Any = None
_device: str | None = None
_threshold: float | None = None
_error: str | None = None


def _model_document(url: str) -> str:
    """Match normalize_test_url in url-transformer-finetuning.ipynb."""
    value = url.strip().lower().replace("[.]", ".")
    if value.startswith("hxxps://"):
        return "https://" + value[8:]
    if value.startswith("hxxp://"):
        return "http://" + value[7:]
    return value if re.match(r"^https?://", value) else "https://" + value


def _load_model() -> bool:
    global _model, _tokenizer, _device, _threshold, _error
    with _lock:
        if _model is not None:
            return True
        try:
            if not (URL_MODEL_PATH / "config.json").is_file():
                raise FileNotFoundError("MODEL_NOT_FOUND")
            metrics = json.loads(
                (URL_MODEL_PATH.parent / "internal_test_metrics.json").read_text(encoding="utf-8")
            )
            threshold = float(metrics["threshold"])
            if not math.isfinite(threshold) or not 0 <= threshold <= 1:
                raise ValueError("INVALID_THRESHOLD")

            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(URL_MODEL_PATH, local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(
                URL_MODEL_PATH, local_files_only=True
            )
            if model.config.num_labels != 2 or model.config.id2label != {0: "NORMAL", 1: "MALICIOUS"}:
                raise ValueError("INVALID_LABEL_MAPPING")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(device).eval()
            _model, _tokenizer, _device, _threshold = model, tokenizer, device, threshold
            _error = None
            return True
        except (ImportError, OSError, ValueError, KeyError, TypeError, RuntimeError) as exception:
            _error = f"{type(exception).__name__}: {exception}"
            return False


def predict_url_risk(url: str) -> tuple[float | None, float | None]:
    with _lock:
        if not _load_model():
            return None, None
        import torch

        encoded = _tokenizer(
            _model_document(url), truncation=True, max_length=256,
            padding=True, return_tensors="pt",
        )
        encoded = {name: value.to(_device) for name, value in encoded.items()}
        with torch.inference_mode():
            logits = _model(**encoded).logits
            probability = float(torch.softmax(logits, dim=-1)[0, 1].cpu())
        return probability, _threshold


def url_model_status() -> dict[str, object]:
    with _lock:
        _load_model()
        return {
            "loaded": _model is not None,
            "modelPath": str(URL_MODEL_PATH),
            "modelType": "transformer",
            "device": _device,
            "threshold": _threshold,
            "error": _error,
        }
