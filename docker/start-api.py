"""Fail early if models cannot load; warm them before accepting requests."""
import sys

sys.path.insert(0, "/app/ocr-service")

from smishing_api.text_model import get_text_model
from smishing_api.url_model import url_model_status
from smishing_api.ocr import get_ocr
import uvicorn

if __name__ == "__main__":
    print("Loading text model...", flush=True)
    get_text_model()
    print("Loading URL model...", flush=True)
    status = url_model_status()
    if not status["loaded"]:
        raise RuntimeError(f"URL model load failed: {status['error']}")
    print("Loading OCR...", flush=True)
    get_ocr()
    uvicorn.run("app:app", host="0.0.0.0", port=8000, workers=1)
