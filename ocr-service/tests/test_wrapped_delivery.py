import pytest

from smishing_api.url_analysis import extract_urls, analyze_url
from smishing_api.domain_registry import lookup_domain
from smishing_api.risk import combine_analysis
from smishing_api.schemas import ReputationResult, TextAnalysisResult, UrlAnalysisResult


MESSAGE = """[CJ대한통운] 배송출발
고객님의 상품이 배송 예정입니다.
배송예정시간: 12-14시
위탁장소 선택, 실시간 배송정보
https://
dxsmapp.cjlogistics.com/mmsp
ush/trust.do?empnum=
TEST123&
trspbillnum=EXAMPLE
무인락커 사용안내
https://www.cjlogistics.com/ko/
newsroom/latest/LT_00000028
일요일에도 신속하게!
"""


@pytest.mark.parametrize("scheme,prefix", [("https://", "https://"), ("https:lL", ""), ("", "")])
def test_wrapped_delivery_urls(scheme, prefix):
    message = MESSAGE.replace("https://\n", scheme + "\n").replace("latest/LT_00000028", "latest/LT_\n00000028")
    assert extract_urls(message) == [
        prefix + "dxsmapp.cjlogistics.com/mmspush/trust.do?empnum=TEST123&trspbillnum=EXAMPLE",
        "https://www.cjlogistics.com/ko/newsroom/latest/LT_00000028",
    ]


@pytest.mark.parametrize("second", ["https://evil.example/a", "evil.example/a", "http://trust.do/a"])
def test_following_independent_url_is_not_hidden(second):
    assert extract_urls("https://www.cjlogistics.com/ko/\n" + second) == [
        "https://www.cjlogistics.com/ko/", second,
    ]


def test_wrapped_link_support_host_is_rejoined():
    message = "Your Link verification code is 123456. To stop receiving these messages, visit support.\nlink.com/sms-opt-out?id=REDA\nCTED"
    addresses = extract_urls(message)
    assert addresses == ["support.link.com/sms-opt-out?id=REDACTED"]
    result = UrlAnalysisResult(
        url="https://support.link.com/sms-opt-out?id=REDACTED",
        verdict="UNKNOWN", riskScore=0.4,
        reputation=ReputationResult(status="NO_API_KEY"),
    )
    assert combine_analysis(TextAnalysisResult(label="NORMAL", riskScore=0.1), [result], message)[0] == "LOW"


def test_documented_cj_idn_domain_is_official():
    message = "[CJ대한통운] 상품이 집화되었습니다. 더 자세한 배송정보 조회 안내 http://앱다운.com"
    assert lookup_domain("http://앱다운.com")["brand"] == "CJ대한통운"
    assert lookup_domain("http://xn--2j1bu56az1a.com")["brand"] == "CJ대한통운"
    assert lookup_domain("http://앱다운.com.evil.example") is None
    result = UrlAnalysisResult(
        url="http://앱다운.com/", verdict="SUSPICIOUS", riskScore=0.6,
        reputation=ReputationResult(status="NO_API_KEY"),
    )
    assert combine_analysis(TextAnalysisResult(label="RISK", riskScore=0.99), [result], message)[0] == "LOW"


@pytest.mark.asyncio
async def test_documented_cj_idn_domain_ignores_model_noise(monkeypatch):
    monkeypatch.setattr("smishing_api.url_analysis.predict_url_risk", lambda url: (0.99, 0.32))
    result = await analyze_url("http://앱다운.com", api_key="")
    assert result.verdict == "NO_KNOWN_THREAT"


@pytest.mark.asyncio
@pytest.mark.parametrize("scheme", ["https://", "https:lL", ""])
@pytest.mark.parametrize("extra,expected", [
    ("", "LOW"),
    ("\n인증번호를 입력하세요.", "MEDIUM"),
    ("\nhttps://evil.example/", "MEDIUM"),
    ("\n자세한 내용은 링크를 클릭하세요. https://evil.example/", "MEDIUM"),
])
async def test_delivery_context_overrides_only_model_scores(monkeypatch, extra, expected, scheme):
    monkeypatch.setattr("smishing_api.url_analysis.predict_url_risk", lambda url: (0.99, 0.32))
    text = MESSAGE.replace("https://\n", scheme + "\n") + extra
    results = [await analyze_url(url, api_key="") for url in extract_urls(text)]
    level, _, reasons, _ = combine_analysis(
        TextAnalysisResult(label="RISK", riskScore=0.99), results, text,
    )
    assert level == expected
    assert not any(reason.startswith("trust.do:") for reason in reasons)
