import hashlib
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("filter_kr_mob", Path(__file__).with_name("filter_kr_mob.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_curated_export_preserves_sources_and_accounts_for_every_message(tmp_path):
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in module.SOURCE.glob("*.json")}
    summary = module.export(output=tmp_path)
    assert summary["source_messages"] == 104
    assert summary["accepted"] + summary["excluded"] == 104
    assert summary["accepted_label_counts"] == {"1": summary["accepted"]}
    assert summary["excluded_by_case"]["benign"] == 31
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in module.SOURCE.glob("*.json")}
    import csv
    with (tmp_path / "accepted.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert all("[TRAINING]" not in r["text"] and r["review_reason"] for r in rows)
    assert len({r["id"] for r in rows}) == len(rows)
    assert not any(r["incident_id"] == "inc-MOB-BEN-005" for r in rows)
