from __future__ import annotations

import httpx
import pytest


@pytest.fixture(autouse=True)
def disable_real_url_model(monkeypatch):
    monkeypatch.setattr("smishing_api.url_analysis.predict_url_risk", lambda url: (None, None))

from smishing_api.schemas import TextAnalysisResult, UrlAnalysisResult, ReputationResult
from smishing_api.risk import combine_analysis
from smishing_api.domain_registry import brand_is_relevant, lookup_domain
from smishing_api.url_analysis import (
    analyze_url,
    extract_urls,
    get_virustotal_report,
    inspect_url_structure,
    normalize_url,
)


def test_extract_urls_returns_empty_list_without_url() -> None:
    assert extract_urls("오늘 저녁 같이 먹자.") == []


def test_extracts_and_normalizes_regular_url() -> None:
    assert extract_urls("확인: https://example.com/order.") == [
        "https://example.com/order"
    ]
    assert normalize_url("https://example.com/order") == (
        "https://example.com/order"
    )


def test_normalizes_hxxp_and_defanged_dot() -> None:
    assert normalize_url("hxxp://parcel[.]invalid") == (
        "http://parcel.invalid/"
    )


@pytest.mark.parametrize(
    ("url", "reason_fragment"),
    [
        ("https://192.0.2.10/pay", "IP 주소"),
        ("https://xn--e1afmkfd.xn--p1ai/", "Punycode"),
        ("https://bit.ly/abc", "단축 URL"),
    ],
)
def test_structure_checks(url: str, reason_fragment: str) -> None:
    _, reasons = inspect_url_structure(url)
    assert any(reason_fragment in reason for reason in reasons)


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_virustotal_200_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-apikey"] == "test-key"
        return httpx.Response(
            200,
            json={
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 2,
                            "suspicious": 1,
                        }
                    }
                }
            },
        )

    async with _client(handler) as client:
        result = await get_virustotal_report(
            "https://example.com/", api_key="test-key", client=client
        )
    assert result.status == "FOUND"
    assert result.malicious == 2
    assert result.suspicious == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected"),
    [(404, "NOT_FOUND"), (429, "RATE_LIMITED")],
)
async def test_virustotal_non_success_responses(
    status_code: int, expected: str
) -> None:
    async with _client(
        lambda request: httpx.Response(status_code)
    ) as client:
        result = await get_virustotal_report(
            "https://example.com/", api_key="test-key", client=client
        )
    assert result.status == expected


@pytest.mark.asyncio
async def test_virustotal_without_api_key_does_not_make_request() -> None:
    result = await get_virustotal_report(
        "https://example.com/", api_key=""
    )
    assert result.status == "NO_API_KEY"


@pytest.mark.asyncio
async def test_virustotal_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    async with _client(handler) as client:
        result = await get_virustotal_report(
            "https://example.com/", api_key="test-key", client=client
        )
    assert result.status == "TIMEOUT"


@pytest.mark.asyncio
async def test_dangerous_url_without_sensitive_request_becomes_caution() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": {
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 4,
                            "suspicious": 0,
                        }
                    }
                }
            },
        )

    async with _client(handler) as client:
        url_result = await analyze_url(
            "https://example.com/", api_key="test-key", client=client
        )
    risk_level, _, _, _ = combine_analysis(
        TextAnalysisResult(label="NORMAL", riskScore=0.05),
        [url_result],
    )
    assert url_result.verdict == "DANGEROUS"
    assert risk_level == "MEDIUM"


def test_unknown_reputation_alone_does_not_raise_grade() -> None:
    unknown = UrlAnalysisResult(
        url="https://example.com/",
        hostname="example.com",
        verdict="UNKNOWN",
        riskScore=0.4,
        reasons=["평판을 확인하지 못했습니다."],
        reputation=ReputationResult(status="TIMEOUT"),
    )
    risk_level, _, _, _ = combine_analysis(
        TextAnalysisResult(label="NORMAL", riskScore=0.05),
        [unknown],
    )
    assert risk_level == "LOW"


def test_high_text_score_without_request_stays_low() -> None:
    risk_level, summary, _, _ = combine_analysis(
        TextAnalysisResult(label="RISK", riskScore=0.99),
        [],
    )
    assert risk_level == "LOW"
    assert "안전이 확인" in summary


def test_high_text_score_with_unknown_url_stays_low() -> None:
    unknown = UrlAnalysisResult(
        url="https://example.com/",
        hostname="example.com",
        verdict="UNKNOWN",
        riskScore=0.4,
        reasons=["평판을 확인하지 못했습니다."],
        reputation=ReputationResult(status="TIMEOUT"),
    )
    risk_level, _, _, _ = combine_analysis(
        TextAnalysisResult(label="RISK", riskScore=0.99),
        [unknown],
    )
    assert risk_level == "LOW"


def test_official_domain_requires_domain_boundary_and_brand_match() -> None:
    official = lookup_domain("https://www.cjlogistics.com/ko/tool/parcel/tracking")
    assert official is not None
    assert official["kind"] == "official"
    assert brand_is_relevant("[CJ대한통운] 배송이 시작되었습니다.", official)
    assert not brand_is_relevant("[한진택배] 배송이 시작되었습니다.", official)
    assert lookup_domain("https://cjlogistics.com.evil.example/login") is None


def test_related_official_url_without_known_threat_is_low() -> None:
    official = UrlAnalysisResult(
        url="https://www.cjlogistics.com/ko/tool/parcel/tracking",
        hostname="www.cjlogistics.com",
        verdict="UNKNOWN",
        riskScore=0.4,
        reasons=["평판 보고서가 없습니다."],
        reputation=ReputationResult(status="NOT_FOUND"),
    )
    risk_level, _, reasons, _ = combine_analysis(
        TextAnalysisResult(label="NORMAL", riskScore=0.05),
        [official],
        "[CJ대한통운] 고객님의 상품이 배송 중입니다.",
    )
    assert risk_level == "LOW"
    assert any("공식 도메인이 일치" in reason for reason in reasons)


def test_messenger_link_without_url_risk_stays_low() -> None:
    messenger = UrlAnalysisResult(
        url="https://open.kakao.com/o/example",
        hostname="open.kakao.com",
        verdict="NO_KNOWN_THREAT",
        riskScore=0.0,
        reasons=[],
        reputation=ReputationResult(status="FOUND"),
    )
    risk_level, _, reasons, _ = combine_analysis(
        TextAnalysisResult(label="NORMAL", riskScore=0.05),
        [messenger],
        "상담은 오픈채팅으로 문의하세요.",
    )
    assert risk_level == "LOW"
    assert any("메신저" in reason for reason in reasons)


def test_explicit_personal_information_request_without_url_is_medium() -> None:
    risk_level, _, reasons, _ = combine_analysis(
        TextAnalysisResult(label="NORMAL", riskScore=0.05),
        [],
        "확인을 위해 인증번호를 입력하세요.",
    )
    assert risk_level == "MEDIUM"
    assert any("인증정보" in reason for reason in reasons)
