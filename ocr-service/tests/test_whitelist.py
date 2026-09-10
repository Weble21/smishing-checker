"""CSV-backed registry and offline policy regression (no OCR/model/VT calls)."""
import csv
from pathlib import Path

import pytest

from smishing_api.domain_registry import brand_is_relevant, load_domain_registry, lookup_domain
from smishing_api.risk import combine_analysis
from smishing_api.schemas import ReputationResult, TextAnalysisResult, UrlAnalysisResult


DATA_DIR = Path(__file__).resolve().parents[2] / "dataset" / "whiteList"
with (DATA_DIR / "message_url_pairs_450.csv").open(encoding="utf-8-sig", newline="") as stream:
    PAIRS = list(csv.DictReader(stream))


def result(url, verdict="UNKNOWN"):
    return UrlAnalysisResult(url=url, verdict=verdict, riskScore=0.4,
                             reasons=[], reputation=ReputationResult(status="NOT_FOUND"))


@pytest.mark.parametrize("row", PAIRS, ids=lambda row: row["id"])
def test_message_url_pair_policy(row):
    # Labels/annotations are test expectations, never inference inputs.
    message = f'{row["message_text"]}\n{row["url"]}'
    level, _, _, _ = combine_analysis(
        TextAnalysisResult(label="NORMAL", riskScore=0.05),
        [result(row["url"])], message,
    )
    # UNKNOWN is deliberately injected: CSV labels must not become model evidence.
    # An unverified URL alone no longer raises the final grade.
    assert level == "LOW"


def test_shared_domain_keeps_all_brands():
    match = lookup_domain("https://www.naver.com/")
    assert brand_is_relevant("[NAVER] 계정 알림", match)
    assert brand_is_relevant("[네이버쇼핑] 배송 알림", match)


@pytest.mark.parametrize("host", ["open.kakao.com", "pf.kakao.com", "line.me"])
def test_messenger_overrides_parent_official_domain(host):
    assert lookup_domain(host)["kind"] == "messenger"


@pytest.mark.parametrize("host", ["evilnaver.com", "naver.com.evil.example", "naver.com@evil.example"])
def test_lookalike_is_not_whitelisted(host):
    assert lookup_domain(host) is None


@pytest.mark.parametrize("verdict,score,expected", [
    ("DANGEROUS", 0.05, "LOW"), ("SUSPICIOUS", 0.05, "LOW"),
    ("UNKNOWN", 0.99, "LOW"),
])
def test_official_domain_set_is_low_despite_url_model_noise(verdict, score, expected):
    level, _, _, _ = combine_analysis(
        TextAnalysisResult(label="NORMAL", riskScore=score),
        [result("https://www.kbstar.com/", verdict)], "[KB국민은행] 알림입니다.",
    )
    assert level == expected


def test_missing_or_invalid_csv_does_not_fall_back_to_seed(tmp_path):
    path = tmp_path / "domains.csv"
    for content in (None, "wrong,header\na,b\n"):
        if content is not None:
            path.write_text(content, encoding="utf-8")
        registry = load_domain_registry(csv_path=str(path))
        assert lookup_domain("kbstar.com", registry) is None
        load_domain_registry.cache_clear()


def test_csv_is_authoritative_and_seed_aliases_are_preserved():
    assert lookup_domain("nps.or.kr") is not None
    assert lookup_domain("baemin.go.link") is not None
    assert lookup_domain("go.link") is None
    assert lookup_domain("epeople.go.kr") is None  # JSON-only domain
    assert brand_is_relevant("[대한통운] 배송 안내", lookup_domain("cjlogistics.com"))
