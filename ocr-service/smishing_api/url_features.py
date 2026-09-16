from __future__ import annotations

import re


INPUT_SCHEMA = "url-structure-v1"
_NUMERIC_SEQUENCE = re.compile(r"\d+")


def url_structure_features(url: str) -> tuple[int, int]:
    """Return the two structural features used by URL model training."""
    value = str(url)
    path_depth = value.count("/")
    numeric_sequences = _NUMERIC_SEQUENCE.findall(value)
    max_numeric_sequence = max((len(sequence) for sequence in numeric_sequences), default=0)
    return path_depth, max_numeric_sequence


def model_document(url: str) -> str:
    """Serialize a URL and its numeric features into the CANINE input text."""
    path_depth, max_numeric_sequence = url_structure_features(url)
    return (
        f"path_depth={path_depth} "
        f"max_numeric_sequence={max_numeric_sequence} "
        f"url={url}"
    )
