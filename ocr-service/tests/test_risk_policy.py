import pytest
from smishing_api.risk import combine_analysis, requests_link_access
from smishing_api.schemas import TextAnalysisResult, UrlAnalysisResult, ReputationResult


def url(verdict, address="https://unverified.example/"):
    return UrlAnalysisResult(url=address, verdict=verdict, riskScore=0.8,
                             reputation=ReputationResult(status="NOT_FOUND"))


def decide(message, urls, score=0.99):
    return combine_analysis(TextAnalysisResult(label="RISK", riskScore=score), urls, message)[0]


@pytest.mark.parametrize("message", ["안녕하세요", "긴급 서비스 중단"])
def test_no_url_is_low(message):
    assert decide(message, []) == "LOW"


@pytest.mark.parametrize("verdict", ["UNKNOWN", "INVALID", "NO_KNOWN_THREAT", "SUSPICIOUS"])
def test_unverified_without_lure_is_caution(verdict):
    assert decide("회의 자료입니다.", [url(verdict)]) == "MEDIUM"


@pytest.mark.parametrize("verdict", ["UNKNOWN", "INVALID", "NO_KNOWN_THREAT", "SUSPICIOUS", "DANGEROUS"])
@pytest.mark.parametrize("score", [0.01, 0.99])
def test_unverified_with_lure_is_high(verdict, score):
    assert decide("링크를 클릭하세요.", [url(verdict)], score) == "HIGH"


@pytest.mark.parametrize("address", ["https://unverified.example/", "https://www.kbstar.com/"])
def test_dangerous_overrides_everything(address):
    assert decide("[국민은행] 공지입니다.", [url("DANGEROUS", address)]) == "HIGH"


@pytest.mark.parametrize("verdict", ["UNKNOWN", "NO_KNOWN_THREAT", "SUSPICIOUS"])
def test_matching_whitelist_is_safe_despite_model_noise(verdict):
    assert decide("[국민은행] 링크를 클릭하세요.", [url(verdict, "https://www.kbstar.com/")]) == "LOW"


@pytest.mark.parametrize("address", ["https://www.shinhan.com/", "https://kbstar.com.evil.example/", "https://kbstar.com@evil.example/"])
def test_mismatch_cannot_be_safe(address):
    assert decide("[국민은행] 안내입니다.", [url("UNKNOWN", address)]) == "MEDIUM"


@pytest.mark.parametrize("other,expected", [("DANGEROUS", "HIGH"), ("UNKNOWN", "MEDIUM")])
def test_mixed_urls_take_highest_risk(other, expected):
    assert decide("[국민은행] 공지", [url("UNKNOWN", "https://kbstar.com"), url(other)]) == expected


def test_missing_url_result_is_not_no_url():
    assert decide("자료 https://unverified.example", []) == "MEDIUM"


@pytest.mark.parametrize("message", [
    "링크를 클릭해서 확인하세요.", "아래 주소로 접속 바랍니다.",
    "신원확인을 완료하지 않은 이용자는 서비스사용이 중단됩니다.",
    "금일 중 미확인 시 자동 반송됩니다.", "갱신하기: https://unverified.example",
])
def test_direct_and_indirect_lures(message):
    assert requests_link_access(message)
    assert decide(message, [url("UNKNOWN")]) == "HIGH"


@pytest.mark.parametrize("message", ["회의 자료 링크가 포함되어 있습니다.", "링크를 클릭하지 마세요.",
    "신원확인 미완료 시 서비스 이용이 중단됩니다. 기존 앱을 직접 열어 확인하세요."])
def test_no_lure_or_app_only(message):
    assert not requests_link_access(message)
    assert decide(message, [url("UNKNOWN")]) == "MEDIUM"

@pytest.mark.parametrize("message", ["인증번호를 알려주세요.", "개인정보를 입력하세요.", "계좌로 송금하세요.", "10만원 보내주세요."])
@pytest.mark.parametrize("official", [False, True])
def test_sensitive_request_is_at_least_caution(message, official):
    urls = [url("UNKNOWN", "https://www.kbstar.com/")] if official else []
    assert decide(message, urls) == "MEDIUM"

@pytest.mark.parametrize("message", ["인증번호를 알려주지 마세요.", "개인정보를 입력하지 마세요.", "계좌로 송금하지 마세요.", "개인정보를 요구하지 않습니다."])
def test_safety_advice_is_not_a_sensitive_request(message):
    assert decide(message, []) == "LOW"


def test_sensitive_request_never_downgrades_dangerous_url():
    assert decide("인증번호를 알려주세요.", [url("DANGEROUS")]) == "HIGH"


@pytest.mark.parametrize("message", ["89,700원이 입금되었습니다.", "결제/주문 내역을 확인하세요.", "송금이 완료되었습니다."])
def test_transaction_notifications_are_not_requests(message):
    assert decide(message, []) == "LOW"


@pytest.mark.parametrize("message", [
    "엄마 나 휴대폰 고장났어. 이 계좌로 30만원 이체해 줘.",
    "이름과 생년월일을 알려주세요.",
    "인증번호를 알려주지 마세요\n아래 계좌로 30만원 송금해주세요",
    "인증번호를 알려주지 마세요, 아래 계좌로 30만원 송금해주세요",
    "신분증을 제출해 주세요.", "전화번호를 회신 바랍니다.",
])
@pytest.mark.parametrize("official", [False, True])
def test_reviewed_request_regressions(message, official):
    urls = [url("UNKNOWN", "https://www.kbstar.com/")] if official else []
    assert decide(message, urls) == "MEDIUM"


@pytest.mark.parametrize("message", ["개인정보 입력이 완료되었습니다.", "이름과 생년월일 등록 완료", "신분증 제출이 완료되었습니다."])
def test_information_completion_is_not_request(message):
    assert decide(message, []) == "LOW"


@pytest.mark.parametrize("joint,score,expected", [(True, .95, "HIGH"), (True, .6, "MEDIUM"), (False, .99, "MEDIUM")])
def test_joint_model_supports_indirect_action_context(joint, score, expected):
    text = TextAnalysisResult(label="RISK", riskScore=score, contextModel=joint)
    message = "회원 혜택 유지에 필요한 정보 보완 https://unverified.example/"
    assert combine_analysis(text, [url("UNKNOWN")], message)[0] == expected


@pytest.mark.parametrize("message", ["회의 자료입니다.", "개인정보 입력이 완료되었습니다.", "개인정보를 알려주지 마세요."])
@pytest.mark.parametrize("address,expected", [(None, "LOW"), ("https://www.kbstar.com/", "LOW"), ("https://unverified.example/", "MEDIUM")])
def test_model_score_alone_cannot_override_url_policy(message, address, expected):
    text = TextAnalysisResult(label="RISK", riskScore=.99, contextModel=True)
    urls = [url("UNKNOWN", address)] if address else []
    assert combine_analysis(text, urls, message)[0] == expected
