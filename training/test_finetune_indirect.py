import csv
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("finetune_indirect", Path(__file__).with_name("finetune_indirect.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def base_splits(tmp_path):
    for split, text in [("train", "저녁 약속"), ("valid", "오전 회의"), ("test", "주말 모임")]:
        with (tmp_path / f"{split}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["text", "label"])
            writer.writeheader()
            writer.writerows([{"text": text, "label": 0}, {"text": text + " 송금 요구", "label": 1}])


def test_keeps_original_splits_and_adds_balanced_seeds(tmp_path):
    base_splits(tmp_path)
    splits = module.prepare(tmp_path)
    assert {name: len(rows) for name, rows in splits.items()} == {"train": 22, "valid": 10, "test": 10}
    for rows in splits.values():
        assert sum(r["label"] == 0 for r in rows) == sum(r["label"] == 1 for r in rows)
    bank_pair = [r for r in splits["train"] if r.get("id") in {"bl01", "bl02"}]
    assert len(bank_pair) == 2
    assert {r["label"] for r in bank_pair} == {0, 1}


def test_rejects_leakage(tmp_path):
    base_splits(tmp_path)
    (tmp_path / "test.csv").write_bytes((tmp_path / "train.csv").read_bytes())
    with pytest.raises(ValueError, match="overlap"):
        module.prepare(tmp_path)


def test_rejects_conflicting_labels(tmp_path):
    base_splits(tmp_path)
    with (tmp_path / "train.csv").open("a", encoding="utf-8") as stream:
        stream.write("저녁 약속,1\n")
    with pytest.raises(ValueError, match="Conflicting"):
        module.prepare(tmp_path)


def test_curated_kr_is_train_only(tmp_path):
    base_splits(tmp_path)
    baseline = module.prepare(tmp_path)
    curated = Path(__file__).with_name("kr_mob_filtered") / "accepted.csv"
    splits = module.prepare(tmp_path, kr_path=curated)
    assert splits["valid"] == baseline["valid"]
    assert splits["test"] == baseline["test"]
    assert sum(r["slice"] == "kr_mob_curated" for r in splits["train"]) == 18
