from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


def _profile_csv(path: Path, source: str, *, labeled: bool) -> dict[str, object]:
    digest = hashlib.sha256()
    rows = missing_urls = empty_urls = 0
    label_counts = {"normal": 0, "malicious": 0} if labeled else None

    with path.open("rb") as binary_file:
        for block in iter(lambda: binary_file.read(1024 * 1024), b""):
            digest.update(block)

    with path.open("r", encoding="utf-8", newline="") as text_file:
        reader = csv.DictReader(text_file)
        required = {"ID", "URL"} | ({"label"} if labeled else set())
        missing_columns = required.difference(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"{path} is missing columns: {sorted(missing_columns)}")
        for row in reader:
            rows += 1
            url = row.get("URL")
            if url is None:
                missing_urls += 1
            elif not url.strip():
                empty_urls += 1
            if labeled:
                label = row["label"].strip()
                if label == "0":
                    label_counts["normal"] += 1
                elif label == "1":
                    label_counts["malicious"] += 1
                else:
                    raise ValueError(f"Unexpected label {label!r} in {path}")

    return {
        "source": source,
        "path": str(path),
        "rows": rows,
        "binary_label_counts": label_counts,
        "missing_urls": missing_urls,
        "empty_urls": empty_urls,
        "size_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def build_data_manifest(
    *, project_dir: Path, output_path: Path, chunk_size: int = 250_000
) -> dict[str, object]:
    del chunk_size  # The reader streams rows and does not retain chunks.
    data_dir = project_dir / "dataset" / "url-training" / "open"
    files = [
        _profile_csv(data_dir / "train.csv", "open_train", labeled=True),
        _profile_csv(data_dir / "test.csv", "open_test", labeled=False),
    ]
    counts = files[0]["binary_label_counts"]
    labeled_rows = int(counts["normal"]) + int(counts["malicious"])
    manifest = {
        "files": files,
        "combined_labeled": {
            "rows": labeled_rows,
            "normal": counts["normal"],
            "malicious": counts["malicious"],
            "malicious_ratio": counts["malicious"] / labeled_rows,
        },
    }
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest
