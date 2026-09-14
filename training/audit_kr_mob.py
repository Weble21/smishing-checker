"""Read-only audit of incident data suitability for SMS-at-receipt training."""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ocr-service"))
from smishing_api.url_analysis import extract_urls, normalize_url
from smishing_api.domain_registry import lookup_domain
from urllib.parse import urlsplit

DATA = ROOT / "dataset/KR-MOB-SMISHING/KR-MOB-SMISHING-100-v1"


def clean(text):
    return re.sub(r"\s+", " ", text.replace("[TRAINING]", "")).strip()


def audit():
    files = sorted((DATA / "incidents").glob("*.json"))
    incidents, messages, failures = [], [], []
    for path in files:
        try:
            incident = json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError) as exc:
            failures.append({"file": path.name, "error": type(exc).__name__})
            continue
        incidents.append(incident)
        for sample in incident.get("message_samples_used", []):
            text = sample.get("text", "")
            messages.append({"id": incident.get("incident_id"), "case": incident.get("case_type"),
                             "text": text, "clean": clean(text), "theme": incident.get("theme")})
    exact, templates = defaultdict(list), defaultdict(list)
    domains, with_urls, official, bad_urls = Counter(), Counter(), Counter(), []
    for row in messages:
        exact[row["clean"]].append(row)
        key = re.sub(r"https?://\S+", "<URL>", row["clean"])
        key = re.sub(r"\d+", "<NUM>", key)
        templates[key].append(row)
        urls = extract_urls(row["clean"])
        if urls:
            with_urls[row["case"]] += 1
        for url in urls:
            try:
                host = urlsplit(normalize_url(url)).hostname or ""
            except ValueError:
                bad_urls.append(row["id"])
                continue
            domains[host] += 1
            if lookup_domain(url):
                official[row["case"]] += 1
    mapping = {"benign": 0, "malicious": 1, "benign_lookalike": 1}
    existing = set()
    sources = [ROOT / "training/indirect_lures.csv", ROOT / "training/brand_link_pairs.csv",
               ROOT / "dataset/whiteList/message_url_pairs_450.csv"]
    for path in sources:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                text = row.get("text") or row.get("message_text", "")
                if row.get("url") and row["url"] not in text:
                    text += " " + row["url"]
                existing.add(clean(text))
    counts = Counter(i.get("case_type") for i in incidents)
    duplicate_groups = [rows for rows in exact.values() if len(rows) > 1]
    cross_label = [rows for rows in exact.values() if len({mapping.get(r["case"]) for r in rows}) > 1]
    result = {
        "json_files": len(files), "parse_failures": failures,
        "incident_case_counts": dict(counts),
        "duplicate_incident_ids": len(incidents) - len({i.get("incident_id") for i in incidents}),
        "theme_counts": dict(Counter(i.get("theme") for i in incidents)),
        "incidents_without_message": [i.get("incident_id") for i in incidents if not i.get("message_samples_used")],
        "sms_sample_count": len(messages), "sms_by_case": dict(Counter(r["case"] for r in messages)),
        "empty_messages": sum(not r["clean"] for r in messages),
        "watermarked_messages": sum("[TRAINING]" in r["text"] for r in messages),
        "messages_with_url_by_case": dict(with_urls), "invalid_url_incidents": sorted(set(bad_urls)),
        "unique_hosts": len(domains), "example_host_count": sum(h.endswith(".example") for h in domains),
        "registered_domain_occurrences_by_case": dict(official),
        "unique_clean_messages": len(exact), "duplicate_message_groups": len(duplicate_groups),
        "exact_conflicting_binary_labels": [[r["id"] for r in rows] for rows in cross_label],
        "unique_templates": len(templates),
        "templates_spanning_incidents": sum(len({r["id"] for r in rows}) > 1 for rows in templates.values()),
        "exact_overlap_with_local_synthetic_sets": sum(r["clean"] in existing for r in messages),
        "sms_event_ground_truth": dict(Counter(e.get("label", {}).get("ground_truth", "missing")
            for i in incidents for e in i.get("event_stream", []) if e.get("event_type") == "sms.received")),
        "note": "Incident outcome labels are not automatically SMS labels. Review benign_lookalike and mixed incidents.",
    }
    return result


if __name__ == "__main__":
    result = audit()
    output = ROOT / "training/kr_mob_audit.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
