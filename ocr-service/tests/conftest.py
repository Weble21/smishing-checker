from __future__ import annotations

import sys
from pathlib import Path

import pytest


SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))


@pytest.fixture(autouse=True)
def disable_external_context_review(monkeypatch):
    # Tests opt in explicitly; developer environment must never send fixture SMSs.
    monkeypatch.delenv("CONTEXT_LLM_MODEL", raising=False)
    monkeypatch.delenv("DYNAMIC_ANALYSIS_ENABLED", raising=False)
    monkeypatch.delenv("DYNAMIC_ANALYSIS_BASE_URL", raising=False)
