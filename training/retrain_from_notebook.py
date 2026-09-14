"""Rebuild the notebook's classifier from its pinned Hub sources plus lure seeds."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

from finetune_indirect import template


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    from datasets import load_dataset
    from huggingface_hub import HfApi
    from sklearn.model_selection import StratifiedGroupKFold
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, set_seed

    set_seed(42)
    model_id = "monologg/koelectra-base-v3-discriminator"
    dataset_id = "meal-bbang/Korean_message"
    hub = HfApi()
    model_sha = hub.model_info(model_id).sha
    dataset_sha = hub.dataset_info(dataset_id).sha
    manifest = {"model_id": model_id, "model_revision": model_sha,
                "dataset_id": dataset_id, "dataset_revision": dataset_sha,
                "source_label_map": {"2": 1, "3": 0},
                "initialization": "Pretrained backbone with newly initialized binary classifier; not deployed weights",
                "seed": 42}
    (args.output / "source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    frame = load_dataset(dataset_id, revision=dataset_sha)["train"].to_pandas()
    frame = frame.loc[frame["class"].isin([2, 3]), ["content", "class"]].copy()
    frame["text"] = frame["content"].map(lambda value: re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()
                                        if isinstance(value, str) else "")
    frame["label"] = frame["class"].map({2: 1, 3: 0}).astype(int)
    frame = frame.loc[frame["text"].ne("")].copy()
    frame["group_id"] = frame["text"].map(template)
    conflicts = frame.groupby("group_id")["label"].nunique()
    frame = frame.loc[~frame["group_id"].isin(conflicts[conflicts > 1].index)]
    frame = frame.drop_duplicates("text").reset_index(drop=True)
    frame["source"] = dataset_id
    chosen = None
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    for train_idx, rest_idx in outer.split(frame, frame.label, frame.group_id):
        train, rest = frame.iloc[train_idx], frame.iloc[rest_idx]
        inner = StratifiedGroupKFold(n_splits=2, shuffle=True, random_state=42)
        for valid_idx, test_idx in inner.split(rest, rest.label, rest.group_id):
            parts = {"train": train, "valid": rest.iloc[valid_idx], "test": rest.iloc[test_idx]}
            if all(set(part.label) == {0, 1} for part in parts.values()):
                chosen = parts
                break
        if chosen:
            break
    if chosen is None:
        raise ValueError("Unable to produce grouped binary splits")
    split_dir = args.output / "base_splits"
    split_dir.mkdir()
    for name, part in chosen.items():
        part[["text", "label", "source", "group_id"]].to_csv(split_dir / f"{name}.csv", index=False)
    print("Original-data split sizes:", {s: len(p) for s, p in chosen.items()}, flush=True)
    initial_dir = args.output / "initial"
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=model_sha)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_id, revision=model_sha, num_labels=2,
        id2label={0: "NORMAL", 1: "RISK"}, label2id={"NORMAL": 0, "RISK": 1},
    )
    model.save_pretrained(initial_dir)
    tokenizer.save_pretrained(initial_dir)
    del model
    # Replace preparation process so its Torch/CUDA context is released before training.
    os.execv(sys.executable, [sys.executable, str(Path(__file__).with_name("finetune_indirect.py")),
                    "--base-splits", str(split_dir), "--model-dir", str(initial_dir),
                    "--output", str(args.output / "trained"), "--epochs", "3"])


if __name__ == "__main__":
    main()
