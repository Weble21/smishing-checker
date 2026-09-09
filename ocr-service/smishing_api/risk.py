from __future__ import annotations

from collections.abc import Iterable

import re

from .config import TEXT_HIGH_THRESHOLD
from .domain_registry import brand_is_relevant, lookup_domain
from .schemas import TextAnalysisResult, UrlAnalysisResult


TEXT_SIGNAL_PATTERNS = {
    "개인정보 또는 인증정보를 요구합니다.": re.compile(
        r"(?i)(주민(?:등록)?번호|개인정보|신용정보|신용카드정보|계좌번호|카드번호|비밀번호|인증번호|"
        r"보안카드|신분증|공동인증서).{0,20}(입력|제출|전송|회신|알려|보내)"
        r"|(입력|제출|전송|회신).{0,20}(주민(?:등록)?번호|개인정보|신용정보|신용카드정보|계좌번호|"
        r"카드번호|비밀번호|인증번호|보안카드|신분증|공동인증서)"
    ),
    "송금·입금 또는 금전 거래를 요구합니다.": re.compile(
        r"(?i)(송금|입금|결제|납부|이체|대출|수수료|보증금|급전).{0,20}"
        r"(요청|필요|바랍니다|하세요|해라|진행|계좌)"
        r"|(계좌|금액|돈|\d+\s*만?\s*원).{0,20}(송금|입금|이체|보내)"
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


def detect_text_signals(message: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", message)
    return [reason for reason, pattern in TEXT_SIGNAL_PATTERNS.items() if pattern.search(normalized)]


def combine_analysis(
    text_analysis: TextAnalysisResult,
    url_analysis: list[UrlAnalysisResult],
    message: str = "",
) -> tuple[str, str, list[str], list[str]]:
    verdicts = {result.verdict for result in url_analysis}
    score = text_analysis.riskScore
    text_signals = detect_text_signals(message)
    official_relevant: list[str] = []
    official_mismatch: list[str] = []
    messenger_links: list[str] = []
    external_links: list[str] = []

    for result in url_analysis:
        domain_match = lookup_domain(result.url)
        if domain_match is None:
            external_links.append(result.hostname or result.url)
        elif domain_match["kind"] == "messenger":
            messenger_links.append(result.hostname or result.url)
        elif brand_is_relevant(message, domain_match):
            official_relevant.append(domain_match["brand"])
        else:
            official_mismatch.append(domain_match["brand"])

    sensitive_requests = [
        reason for reason in text_signals
        if reason in {
            "개인정보 또는 인증정보를 요구합니다.",
            "송금·입금 또는 금전 거래를 요구합니다.",
        }
    ]
    # URL verdicts take precedence; text-only caution requires a concrete request.
    if verdicts & {"DANGEROUS", "SUSPICIOUS"}:
        risk_level = "HIGH"
    elif not url_analysis and sensitive_requests:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    reasons: list[str] = []
    reasons.extend(text_signals)
    if score >= TEXT_HIGH_THRESHOLD:
        reasons.append("문자 모델 점수는 참고 정보이며, 이 점수만으로 위험 등급을 올리지 않습니다.")
    if not sensitive_requests:
        reasons.append("개인정보·신용정보 요구나 송금 유도가 감지되지 않았습니다.")

    for brand in official_relevant:
        reasons.append(f"{brand}: 문자 속 브랜드와 공식 도메인이 일치합니다.")
    for brand in official_mismatch:
        reasons.append(f"{brand}: 공식 도메인이지만 문자 내용과 브랜드 연관성을 확인하지 못했습니다.")
    for host in messenger_links:
        reasons.append(f"{host}: 메신저로 연결되는 주소이므로 상대방을 추가 확인해야 합니다.")
    for host in external_links:
        reasons.append(f"{host}: 등록된 공식 도메인이 아니어서 문자 내용과의 연관성을 확인하지 못했습니다.")

    for result in url_analysis:
        prefix = result.hostname or result.url
        for reason in result.reasons:
            reasons.append(f"{prefix}: {reason}")

    if "DANGEROUS" in verdicts:
        reasons.insert(0, "보안 평판 검사에서 악성 URL이 확인되었습니다.")

    if not url_analysis:
        reasons.append("문자에서 URL이 추출되지 않았습니다.")

    if risk_level == "HIGH":
        summary = (
            "보안 평판 검사에서 악성 URL이 확인되었습니다."
            if "DANGEROUS" in verdicts
            else "URL 분석에서 위험 신호가 감지되어 스미싱 가능성이 높습니다."
        )
        actions = [
            "문자 속 링크를 누르거나 파일을 내려받지 마세요.",
            "송금하거나 개인정보와 인증번호를 입력하지 마세요.",
            "국번 없이 118에 상담하고, 이미 피해가 발생했거나 긴급하면 112에 신고하세요.",
        ]
    elif risk_level == "MEDIUM":
        summary = "URL은 없지만 개인정보·신용정보 요구 또는 송금 유도가 있어 주의가 필요합니다."
        actions = [
            "문자 속 링크 대신 해당 기관의 공식 앱이나 대표번호로 확인하세요.",
            "확인 전에는 송금하거나 개인정보를 입력하지 마세요.",
            "의심되면 국번 없이 118에 문의하세요.",
        ]
    else:
        summary = "설정된 위험·주의 판정 조건에 해당하지 않습니다. 안전이 확인됐다는 뜻은 아닙니다."
        actions = [
            "발신자가 예상한 곳인지 공식 앱이나 기존 연락처로 한 번 더 확인하세요.",
            "추가로 링크 클릭이나 개인정보 입력을 요구하면 다시 검사하세요.",
        ]

    return risk_level, summary, _unique(reasons), actions


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
