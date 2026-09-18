from __future__ import annotations

from collections.abc import Iterable

import re

from .domain_registry import brand_is_relevant, lookup_domain
from .schemas import TextAnalysisResult, UrlAnalysisResult


# Match an affirmative request, not just an action noun (e.g. 입력 완료).
REQUEST_END = r"(?:해\s*(?:주|줘|요)|하\s*세요|하\s*십시오|바랍니다|부탁|요청|필요|해야|하셔야|해라)"
PRIVATE_DATA = r"(?:주민(?:등록)?번호|개인정보|신용정보|신용카드정보|계좌번호|카드번호|비밀번호|인증번호|보안카드|신분증|공동인증서|이름|성명|생년월일|전화번호|연락처|집\s*주소|복구문구|복구\s*단어)"
PRIVATE_ACTION = (
    r"(?:(?:입력|제출|전송|회신|공유|등록)(?:을|를)?\s*" + REQUEST_END
    + r"|알려\s*(?:주|줘)|보내\s*(?:주|줘|세요)|(?:요구|요청)합니다)"
)
TEXT_SIGNAL_PATTERNS = {
    "개인정보 또는 인증정보를 요구합니다.": re.compile(
        PRIVATE_DATA + r".{0,60}" + PRIVATE_ACTION
        + r"|" + PRIVATE_ACTION + r".{0,40}" + PRIVATE_DATA, re.I
    ),
    "송금·입금 또는 금전 거래를 요구합니다.": re.compile(
        r"(?:송금|입금|이체|납부|결제)(?:을|를)?\s*" + REQUEST_END
        + r"|(?:계좌|금액|돈|[\d,]+\s*만?\s*원).{0,30}보내\s*(?:주|줘|라|세)"
        + r"|(?:수수료|보증금).{0,15}(?:입금|송금|납부).{0,8}(?:필요|요청)", re.I
    ),
    "긴급하게 행동하도록 재촉합니다.": re.compile(
        r"(?i)(긴급|즉시|지금 바로|오늘까지|\d+시간 이내|곧.{0,8}(정지|차단|압류)|"
        r"마지막 경고|기한 초과)"
    ),
    "해외 또는 국제 발신으로 표시된 문자입니다.": re.compile(
        r"(?i)(해외발신|국외발신|국제발신|해외 발신|국외 발신)"
    ),
    "구체적인 설명 없이 확인이나 조치를 요구합니다.": re.compile(
        r"(?i)(본인.?확인|정보.?확인|확인.{0,8}(바랍니다|하세요)|"
        r"조치.{0,8}(바랍니다|하세요)).{0,30}(링크|주소|접속|클릭|입력)"
    ),
}
LINK_ACCESS_PATTERN = re.compile(
    r"(?i)(?:링크|URL|주소).{0,25}"
    r"(?:누르|클릭|접속|방문|열어|들어가|확인|조회|신청|인증|입력)"
    r"|(?:누르|클릭|접속|방문|열어|들어가).{0,15}(?:주세요|하세요|바랍니다|필요)"
    r"|(?:확인|조회|신청|인증).{0,15}(?:https?://|hxxps?://|www\.)"
)
IDENTITY_PATTERN = re.compile(r"신원\s*확인|본인\s*인증|본인\s*확인|KYC", re.I)
SERVICE_THREAT_PATTERN = re.compile(
    r"(?:서비스|이용|사용|계정|거래).{0,25}(?:중단|정지|제한|차단|삭제)"
)


def detect_text_signals(message: str) -> list[str]:
    # Preserve sentence/newline boundaries; a warning must not erase later requests.
    clauses = [re.sub(r"[ \t]+", " ", part) for part in re.split(r"[\r\n.!?。;]+", message)]
    # Remove only the negated action itself, never the whole surrounding sentence.
    clauses = [re.sub(
        r"(?:입력|제출|전송|회신|송금|입금|이체|공유|알려주|보내|요구|요청)(?:하)?지\s*(?:마세요|마십시오|않습니다|말아)",
        "[금지행동]", part) for part in clauses]
    return [reason for reason, pattern in TEXT_SIGNAL_PATTERNS.items()
            if any(pattern.search(part) for part in clauses)]


def model_supported_lure(message: str, analysis: TextAnalysisResult) -> bool:
    """Use only the joint-input model, with observable action context as a guard.

    0.9 is a conservative policy threshold, not a calibrated confidence guarantee.
    A generic binary risk score alone is not evidence of a link invitation.
    """
    if not analysis.contextModel or analysis.label != "RISK" or analysis.riskScore < 0.9:
        return False
    if re.search(r"(?:기존|평소|설치한).{0,20}앱", message):
        return False
    for part in re.split(r"[\r\n.!?。;]+", message):
        if re.search(r"(?:하지|주지|내지)\s*(?:마|않)|완료되|자동으로|추가 결제는 없", part):
            continue
        if re.search(r"(?:정보|서류|인증|카드).{0,12}(?:보완|갱신|등록).{0,15}(?:필요|대상|유지|건만)"
                     r"|(?:필요한|유지를 위한).{0,12}(?:정보 보완|카드 갱신)"
                     r"|(?:배송비|수수료).{0,15}정산.{0,12}(?:후|수령|처리)", part):
            return True
    return False


def requests_link_access(message: str) -> bool:
    """Recognize direct requests and consequence-based indirect link lures."""
    normalized = re.sub(r"\s+", " ", message)
    # Do not treat warnings against visiting links as invitations.
    positive = re.sub(r"[^.!?。]*(?:클릭|접속|누르|방문).{0,12}(?:하지\s*마|지\s*마|금지)[^.!?。]*", " ", normalized)
    app_only = re.search(r"(?:기존|평소|설치한).{0,20}앱.{0,15}(?:직접|열어|실행)", positive)
    direct_text = re.sub(r"[^.!?。]*(?:기존|평소|설치한).{0,20}앱[^.!?。]*", " ", positive)
    if LINK_ACCESS_PATTERN.search(direct_text):
        return True
    if app_only:
        return False
    identity_threat = IDENTITY_PATTERN.search(positive) and SERVICE_THREAT_PATTERN.search(positive)
    consequence = re.search(r"(?:미확인|미제출|미등록|미신청|미납|미완료|않으면|않을\s*경우).{0,45}(?:반송|취소|소멸|정지|중단|제한)", positive)
    action_page = re.search(r"(?:확인|조회|갱신|해제|신청|납부|설치|업데이트)\s*(?:하기|페이지|화면|:)", positive)
    return bool(identity_threat or consequence or action_page)


def combine_analysis(
    text_analysis: TextAnalysisResult,
    url_analysis: list[UrlAnalysisResult],
    message: str = "",
) -> tuple[str, str, list[str], list[str]]:
    from .domain_registry import load_domain_registry
    from .url_analysis import URL_PATTERN, extract_urls, normalize_url

    body = URL_PATTERN.sub(" ", message)
    registry = load_domain_registry()
    has_brand = any(brand_is_relevant(body, {**service, "kind": "official"})
                    for service in registry.get("official_services", []))
    reasons = detect_text_signals(message)
    states = []
    covered = set()
    for result in url_analysis:
        try:
            normalized = normalize_url(result.url)
            covered.add(normalized)
            match = lookup_domain(normalized, registry)
        except ValueError:
            match = None
        host = result.hostname or result.url
        if result.verdict == "DANGEROUS":
            states.append("dangerous")
            reasons.append(f"{host}: URL 분석에서 위험으로 판정되었습니다.")
        elif (match and match["kind"] == "official" and result.verdict != "INVALID"
              and (not has_brand or brand_is_relevant(body, match))):
            states.append("safe")
            reasons.append(f"{host}: 화이트리스트의 공식 도메인이 일치합니다.")
        else:
            states.append("unknown")
            reasons.append(f"{host}: 해당 기관의 안전한 URL인지 확인되지 않았습니다.")
            if match and match["kind"] == "messenger":
                reasons.append(f"{host}: 메신저 주소는 상대방의 신원을 보장하지 않습니다.")
        reasons.extend(f"{host}: {reason}" for reason in result.reasons)

    # A missing analysis result must not turn a visible URL into 'no URL'.
    for candidate in extract_urls(message):
        # Domain-shaped registered brand headers such as [SSG.COM] are not links.
        if "[" + candidate + "]" in message and lookup_domain(candidate, registry):
            continue
        try:
            missing = normalize_url(candidate) not in covered
        except ValueError:
            missing = True
        if missing:
            states.append("unknown")
            reasons.append("문자에 URL이 있으나 해당 URL의 분석 결과가 없습니다.")

    learned_lure = "unknown" in states and model_supported_lure(message, text_analysis)
    lure = bool(states) and (requests_link_access(message) or learned_lure)
    if learned_lure:
        reasons.append("미확인 URL과 행동 요구 문맥을 문자 모델이 위험으로 평가했습니다.")
    sensitive_request = any(reason in {
        "개인정보 또는 인증정보를 요구합니다.",
        "송금·입금 또는 금전 거래를 요구합니다.",
    } for reason in reasons)
    coercive_lure = bool(re.search(
        r"(?:미확인|미제출|미등록|미신청|미납|미완료|않으면|않을\s*경우).{0,45}"
        r"(?:반송|취소|소멸|정지|중단|제한)", message,
    ))
    identity_threat = bool(IDENTITY_PATTERN.search(message) and SERVICE_THREAT_PATTERN.search(message))
    strong_lure = learned_lure or (lure and (sensitive_request or coercive_lure or identity_threat))
    if "dangerous" in states:
        level, summary = "HIGH", "위험한 URL이 포함되어 있습니다."
    elif "unknown" in states and strong_lure:
        level, summary = "HIGH", "안전 여부가 미확인인 URL로 접속을 유도해 스미싱 가능성이 높습니다."
    elif "unknown" in states:
        level, summary = "MEDIUM", "URL의 안전 여부를 확인하지 못해 주의가 필요합니다."
    elif states:
        level, summary = "LOW", "모든 URL이 공식 도메인 화이트리스트 기준을 충족합니다."
    else:
        level, summary = "LOW", "URL이 없어 URL 우선 기준에서 안전으로 분류했습니다."
        reasons.append("URL이 없는 송금 사기 등까지 안전하다는 보장은 아닙니다.")
    sensitive = any(reason in {
        "개인정보 또는 인증정보를 요구합니다.",
        "송금·입금 또는 금전 거래를 요구합니다.",
    } for reason in reasons)
    if sensitive and level == "LOW":
        level, summary = "MEDIUM", "개인정보·인증정보 요구 또는 송금 요청이 있어 주의가 필요합니다."
        reasons = [r for r in reasons if r != "URL이 없는 송금 사기 등까지 안전하다는 보장은 아닙니다."]
    if lure:
        reasons.append("문자에 직접 또는 간접적인 링크 접속 유도가 있습니다.")
    elif states:
        reasons.append("문자에서 링크 접속 유도가 감지되지 않았습니다.")
    if level == "LOW":
        actions = ["발신자와 안내 내용은 기존 앱이나 공식 연락처로 확인하세요."]
    else:
        actions = ["문자 속 링크 대신 기존 앱이나 공식 연락처로 확인하세요.",
                   "확인 전에는 개인정보·인증번호를 입력하거나 송금하지 마세요."]
    return level, summary, _unique(reasons), actions


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
