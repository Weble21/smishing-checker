from __future__ import annotations

import threading
from typing import Any

from .config import resolve_model_dir
from .schemas import TextAnalysisResult


_model: Any | None = None
_tokenizer: Any | None = None
_device: str | None = None
_model_lock = threading.RLock()


def model_status() -> dict[str, object]:
    return {
        "loaded": _model is not None,
        "device": _device,
        "modelDir": str(resolve_model_dir()),
    }


def get_text_model() -> tuple[Any, Any, str]:
    global _model, _tokenizer, _device
    if _model is not None and _tokenizer is not None and _device is not None:
        return _model, _tokenizer, _device

    with _model_lock:
        if _model is None or _tokenizer is None or _device is None:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            model_dir = resolve_model_dir()
            if not (model_dir / "config.json").is_file():
                raise RuntimeError(
                    "KoELECTRA model was not found. Set SMISHING_MODEL_DIR."
                )
            _device = "cuda" if torch.cuda.is_available() else "cpu"
            _tokenizer = AutoTokenizer.from_pretrained(
                model_dir,
                local_files_only=True,
            )
            _model = AutoModelForSequenceClassification.from_pretrained(
                model_dir,
                local_files_only=True,
            ).to(_device)
            _model.eval()

    return _model, _tokenizer, _device


def predict_text(text: str) -> TextAnalysisResult:
    """Run the saved binary NORMAL/RISK KoELECTRA classifier."""
    import torch

    model, tokenizer, device = get_text_model()
    encoded = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=256,
        padding=False,
    )
    encoded = {name: value.to(device) for name, value in encoded.items()}
    with _model_lock, torch.inference_mode():
        logits = model(**encoded).logits
        probabilities = torch.softmax(logits, dim=-1)[0]
        risk_score = float(probabilities[1].detach().cpu())

    return TextAnalysisResult(
        label="RISK" if risk_score >= 0.5 else "NORMAL",
        riskScore=round(risk_score, 4),
    )
