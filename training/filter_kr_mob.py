"""Export a conservative, explicitly reviewed SMS subset; never change source incidents."""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dataset/KR-MOB-SMISHING/KR-MOB-SMISHING-100-v1/incidents"
OUTPUT = ROOT / "training/kr_mob_filtered"

# Per-incident review of message_samples_used, not automatic case_type mapping.
# All messages in these incidents were inspected. They remain synthetic risk examples,
# not proof that unknown domains or these phrases are malicious in real traffic.
REVIEWED = {
    **{f"inc-MOB-BEN-{n:03}": "가족 사칭 상황과 급한 대리 송금 요청을 링크로 연결함"
       for n in (8, 18, 20, 50, 70, 88, 89)},
    **{f"inc-MOB-MAL-{n:03}": "가족 사칭 상황과 급한 대리 송금·결제 요청을 링크로 연결함"
       for n in (1, 33, 83)},
    **{f"inc-MOB-MAL-{n:03}": "24시간 내 인증·조치를 하지 않으면 계정 영구 정지라는 압박과 링크 유도가 결합됨"
       for n in (21, 52, 62, 74, 91)},
    "inc-MOB-MAL-013": "합격 취소 압박과 링크를 통한 본인 인증·가족관계증명서 제출 요구가 결합됨",
    "inc-MOB-MAL-044": "합격 취소 압박과 링크를 통한 입사 증빙·신원 확인 요구가 결합됨",
}


def clean(text):
    return re.sub(r"\s+", " ", text.replace("[TRAINING]", "")).strip()


def export(source=SOURCE, output=OUTPUT):
    accepted, excluded, hashes = [], [], {}
    for path in sorted(source.glob("*.json")):
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        incident = json.loads(path.read_text(encoding="utf-8-sig"))
        for index, sample in enumerate(incident.get("message_samples_used", [])):
            identifier = incident["incident_id"]
            row = {"id": f"{identifier}:sms-{index+1}", "incident_id": identifier,
                   "source_case_type": incident["case_type"], "theme": incident.get("theme", ""),
                   "text": clean(sample.get("text", "")), "label": "",
                   "source": "KR-MOB-SMISHING-v1", "data_origin": "synthetic",
                   "review_reason": ""}
            if identifier in REVIEWED and incident["case_type"] in {"malicious", "benign_lookalike"}:
                row.update(label=1, review_reason=REVIEWED[identifier])
                accepted.append(row)
            else:
                if incident["case_type"] == "benign":
                    reason = ("정상 사건 라벨을 뒷받침하는 발신자·공식 도메인 근거를 문자에서 확인할 수 없음; "
                              "사기와 유사한 표현을 정상으로 또는 반대로 재라벨링하지 않고 보류")
                else:
                    reason = ("일반 인증서·배송·결제·요금·채용 안내와 겹치며 가상 링크도 공식 여부 확인 불가; "
                              "사건 후속 로그 없이 수신 문자만으로 확정 학습하기 어려워 보류")
                row["review_reason"] = reason
                excluded.append(row)
    output.mkdir(parents=True, exist_ok=True)
    fields = ["id", "incident_id", "source_case_type", "theme", "text", "label",
              "source", "data_origin", "review_reason"]
    for filename, rows in (("accepted.csv", accepted), ("excluded.csv", excluded)):
        with (output / filename).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    summary = {"source_messages": len(accepted) + len(excluded), "accepted": len(accepted),
               "excluded": len(excluded),
               "accepted_by_case": dict(Counter(r["source_case_type"] for r in accepted)),
               "excluded_by_case": dict(Counter(r["source_case_type"] for r in excluded)),
               "accepted_label_counts": dict(Counter(str(r["label"]) for r in accepted)),
               "source_sha256": hashes,
               "training_status": "Not merged; risk-only supplement, not a standalone training/evaluation set",
               "license": "CC BY-NC 4.0; KR-MOB-SMISHING Project (2026)",
               "changes": "Removed TRAINING watermark, normalized whitespace, selected reviewed risk examples; source JSON unchanged"}
    (output / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    result = export()
    print(json.dumps({k: v for k, v in result.items() if k != "source_sha256"}, ensure_ascii=False, indent=2))
