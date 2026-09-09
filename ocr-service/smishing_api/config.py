from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(
    os.getenv(
        "SMISHING_PROJECT_DIR",
        Path(__file__).resolve().parents[2],
    )
).resolve()

MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", 10 * 1024 * 1024))
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
OCR_MIN_CONFIDENCE = float(os.getenv("OCR_MIN_CONFIDENCE", "0.55"))
OCR_DEVICE = os.getenv("OCR_DEVICE", "cpu")

TEXT_HIGH_THRESHOLD = float(os.getenv("TEXT_HIGH_THRESHOLD", "0.80"))
TEXT_MEDIUM_THRESHOLD = float(os.getenv("TEXT_MEDIUM_THRESHOLD", "0.60"))
URL_SUSPICIOUS_THRESHOLD = float(
    os.getenv("URL_SUSPICIOUS_THRESHOLD", "0.40")
)
VT_TIMEOUT_SECONDS = float(os.getenv("VT_TIMEOUT_SECONDS", "5"))
DOMAIN_SEED_PATH = Path(
    os.getenv(
        "DOMAIN_SEED_PATH",
        PROJECT_DIR / "config" / "official_domain_seeds.json",
    )
).expanduser().resolve()
OFFICIAL_DOMAINS_PATH = Path(
    os.getenv("OFFICIAL_DOMAINS_PATH")
    or PROJECT_DIR / "dataset" / "whiteList" / "official_domains.csv"
).expanduser().resolve()
URL_MODEL_PATH = Path(
    os.getenv("URL_MODEL_PATH")
    or PROJECT_DIR / "experiments" / "canine-url-v1" / "model"
).expanduser().resolve()


def resolve_model_dir() -> Path:
    configured = os.getenv("SMISHING_MODEL_DIR")
    if configured:
        return Path(configured).expanduser().resolve()

    experiment_root = PROJECT_DIR / "experiments"
    candidates = sorted(
        path.parent
        for path in experiment_root.glob("koelectra-*/model/config.json")
    )
    if not candidates:
        return PROJECT_DIR / "model"
    return candidates[-1]
