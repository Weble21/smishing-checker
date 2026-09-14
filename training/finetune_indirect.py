"""Offline continual fine-tuning from an existing classifier and frozen splits."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

SEEDS = Path(__file__).with_name("indirect_lures.csv")
BRAND_SEEDS = Path(__file__).with_name("brand_link_pairs.csv")


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        if not row.get("text", "").strip() or str(row.get("label")) not in {"0", "1"}:
            raise ValueError(f"Invalid text/label in {path}")
        row["label"] = int(row["label"])
    return rows


def template(text):
    text = re.sub(r"https?://\S+", "<URL>", text.casefold())
    return re.sub(r"\s+", "", re.sub(r"\d+", "<NUM>", text))


def prepare(base_dir, seed_path=SEEDS, brand_seed_path=BRAND_SEEDS):
    seeds = read_rows(seed_path)
    seeds += read_rows(brand_seed_path)
    families = {}
    for row in seeds:
        if row["split"] not in {"train", "valid", "test"}:
            raise ValueError("Unknown split")
        previous = families.setdefault(row["family"], row["split"])
        if previous != row["split"]:
            raise ValueError("Scenario family leaks across splits")
    splits = {}
    owners = {}
    for split in ("train", "valid", "test"):
        rows = [{**row, "source": row.get("source", "existing"), "slice": "existing"}
                for row in read_rows(Path(base_dir) / f"{split}.csv")]
        rows += [{**row, "slice": "brand_link" if row["id"].startswith("bl") else "indirect_lure"}
                 for row in seeds if row["split"] == split]
        seen = {}
        unique = []
        for row in rows:
            key = template(row["text"])
            if key in owners and owners[key] != split:
                raise ValueError("Text/template overlap between frozen splits; resolve before training")
            owners[key] = split
            # A URL-swapped pair may have opposite labels in the SAME split.
            # Keep exact-text identity separate from the split-leakage template.
            identity = re.sub(r"\s+", " ", row["text"]).strip()
            if identity in seen:
                if seen[identity] != row["label"]:
                    raise ValueError("Conflicting labels for the same template")
                continue
            seen[identity] = row["label"]
            unique.append(row)
        if {row["label"] for row in unique} != {0, 1}:
            raise ValueError("Each split needs NORMAL and RISK examples")
        splits[split] = unique
    return splits


def metrics(labels, predictions):
    tp = sum(y == 1 and p == 1 for y, p in zip(labels, predictions))
    fn = sum(y == 1 and p == 0 for y, p in zip(labels, predictions))
    fp = sum(y == 0 and p == 1 for y, p in zip(labels, predictions))
    tn = sum(y == 0 and p == 0 for y, p in zip(labels, predictions))
    return {"count": len(labels), "risk_recall": tp / max(tp + fn, 1),
            "risk_precision": tp / max(tp + fp, 1),
            "normal_false_positive_rate": fp / max(fp + tn, 1)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-splits", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--epochs", type=float, default=2)
    parser.add_argument("--cpu", action="store_true", help="Use CPU explicitly when GPU is unavailable")
    args = parser.parse_args()
    splits = prepare(args.base_splits)
    if not args.prepare_only and (not args.model_dir or not (args.model_dir / "config.json").is_file()):
        parser.error("Existing local model directory with config.json is required; no download is performed")
    # Never overwrite an existing experiment or active model.
    args.output.mkdir(parents=True, exist_ok=False)
    for split, rows in splits.items():
        with (args.output / f"{split}.json").open("w", encoding="utf-8") as stream:
            json.dump(rows, stream, ensure_ascii=False, indent=2)
    manifest = {"seed": 42, "model": str(args.model_dir), "seed_data": str(SEEDS),
                "seed_sha256": hashlib.sha256(SEEDS.read_bytes()).hexdigest(),
                "brand_seed_sha256": hashlib.sha256(BRAND_SEEDS.read_bytes()).hexdigest(),
                "input_schema": "message-domain-v1",
                "base_sha256": {s: hashlib.sha256((args.base_splits / f"{s}.csv").read_bytes()).hexdigest()
                                for s in splits},
                "sizes": {s: len(rows) for s, rows in splits.items()},
                "limitations": ["Synthetic seed examples; not verified incidents or a production accuracy benchmark",
                                "Original base splits must be from the checkpoint's original experiment"]}
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.prepare_only:
        print(json.dumps(manifest["sizes"]))
        return

    import numpy as np
    import torch
    from datasets import Dataset
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              DataCollatorWithPadding, Trainer, TrainingArguments, set_seed)
    set_seed(42)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ocr-service"))
    from smishing_api.message_context import INPUT_SCHEMA, encode_message
    from smishing_api.config import DOMAIN_SEED_PATH, OFFICIAL_DOMAINS_PATH
    manifest["domain_sources"] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (DOMAIN_SEED_PATH, OFFICIAL_DOMAINS_PATH)}
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(args.model_dir, local_files_only=True)
    if model.config.num_labels != 2:
        raise ValueError("Expected existing binary NORMAL=0 / RISK=1 classifier")
    model.config.smishing_input_schema = INPUT_SCHEMA
    tokenized = {}
    for split, rows in splits.items():
        dataset = Dataset.from_list([{"text": r["text"], "labels": r["label"]} for r in rows])
        tokenized[split] = dataset.map(lambda row: encode_message(tokenizer, row["text"]),
                                       remove_columns=["text"])
    trainer = Trainer(model=model, processing_class=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
        train_dataset=tokenized["train"], eval_dataset=tokenized["valid"],
        args=TrainingArguments(output_dir=str(args.output / "checkpoints"),
            learning_rate=1e-5, num_train_epochs=args.epochs, per_device_train_batch_size=8,
            per_device_eval_batch_size=16, eval_strategy="epoch", save_strategy="epoch",
            load_best_model_at_end=True, metric_for_best_model="eval_loss",
            greater_is_better=False, save_total_limit=2, report_to="none", seed=42,
            use_cpu=args.cpu, fp16=not args.cpu and torch.cuda.is_available()))

    def evaluate_slices():
        prediction = trainer.predict(tokenized["test"])
        predicted = np.argmax(prediction.predictions, axis=-1).tolist()
        return {name: metrics([r["label"] for r in splits["test"] if name == "all" or r["slice"] == name],
                              [p for r, p in zip(splits["test"], predicted) if name == "all" or r["slice"] == name])
                for name in ("all", "existing", "indirect_lure", "brand_link")}

    before = evaluate_slices()
    trainer.train()
    after = evaluate_slices()
    # Candidate path is intentionally outside automatic koelectra-* discovery.
    trainer.save_model(str(args.output / "candidate"))
    tokenizer.save_pretrained(args.output / "candidate")
    (args.output / "comparison.json").write_text(
        json.dumps({"before": before, "after": after}, indent=2), encoding="utf-8")
    print("Candidate saved; serving configuration was not changed.")


if __name__ == "__main__":
    main()
