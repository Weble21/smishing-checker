from __future__ import annotations

import base64
import ipaddress
import os
import re
from collections.abc import Iterable
from urllib.parse import SplitResult, urlsplit, urlunsplit

import httpx
from starlette.concurrency import run_in_threadpool

from .config import URL_SUSPICIOUS_THRESHOLD, VT_TIMEOUT_SECONDS
from .domain_registry import lookup_domain
from .schemas import ReputationResult, UrlAnalysisResult
from .url_model import predict_url_risk


URL_PATTERN = re.compile(
    r"(?i)(?:(?:https?|hxxps?)://|www\.)[^\s<>\"']+"
    r"|(?:[a-z0-9\-]+(?:\[\.\]|\.)){1,}[a-z]{2,}(?:/[^\s<>\"']*)?"
)
TRAILING_PUNCTUATION = ".,;:!?)]}>\"'，。！？、」』】）"
SHORTENERS = {
    "bit.ly",
    "cutt.ly",
    "han.gl",
    "is.gd",
    "me2.do",
    "naver.me",
    "t.co",
    "tinyurl.com",
    "url.kr",
}
SUSPICIOUS_PATH_PATTERN = re.compile(
    r"(?i)(login|signin|verify|auth|refund|delivery|parcel|payment|pay|"
    r"인증|로그인|환급|배송|결제)"
)


def extract_urls(text: str) -> list[str]:
    """Extract URLs in appearance order without returning duplicates."""
    if not text:
        return []
    text = _join_wrapped_urls(text)
    seen: set[str] = set()
    results: list[str] = []
    for match in URL_PATTERN.finditer(text):
        candidate = match.group(0).rstrip(TRAILING_PUNCTUATION)
        if candidate and candidate not in seen:
            seen.add(candidate)
            results.append(candidate)
    return results


def _join_wrapped_urls(text: str) -> str:
    """Rejoin OCR URL lines without consuming a following independent URL."""
    lines: list[str] = []
    for raw in text.replace("\\.", ".").splitlines():
        line = raw.strip()
        previous = lines[-1] if lines else ""
        scheme_only = re.fullmatch(r"(?i)(?:https?|hxxps?)://", previous)
        continuation = False
        # OCR can corrupt a standalone scheme (e.g. https:lL). A bare
        # hostname with a path still establishes URL continuation context.
        if previous and URL_PATTERN.fullmatch(previous):
            try:
                candidate = previous if re.match(r"(?i)^(?:https?|hxxps?)://", previous) else "https://" + previous
                continuation = bool(urlsplit(candidate).path)
            except ValueError:
                pass
        ascii_url_piece = bool(re.fullmatch(r"[A-Za-z0-9._~:/?#\[\]@!$&()*+,;=%-]+", line))
        independent_url = URL_PATTERN.match(line) is not None
        if ascii_url_piece and (scheme_only or (continuation and not independent_url)):
            lines[-1] += line
        else:
            lines.append(line)
    return "\n".join(lines)


def normalize_url(url: str) -> str:
    candidate = (url or "").strip().rstrip(TRAILING_PUNCTUATION)
    candidate = re.sub(r"(?i)^hxxps://", "https://", candidate)
    candidate = re.sub(r"(?i)^hxxp://", "http://", candidate)
    candidate = candidate.replace("[.]", ".")
    if not re.match(r"(?i)^https?://", candidate):
        candidate = "https://" + candidate

    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Invalid HTTP URL")
    try:
        parsed.port
    except ValueError as exception:
        raise ValueError("Invalid URL port") from exception
    if any(char.isspace() for char in parsed.netloc):
        raise ValueError("Invalid URL host")

    normalized = SplitResult(
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path or "/",
        parsed.query,
        "",
    )
    return urlunsplit(normalized)


def inspect_url_structure(url: str) -> tuple[float, list[str]]:
    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    reasons: list[str] = []
    score = 0.0

    if parsed.scheme == "http":
        score += 0.25
        reasons.append("암호화되지 않은 HTTP 주소입니다.")
    if _is_ip_address(hostname):
        score += 0.45
        reasons.append("도메인 대신 IP 주소를 사용합니다.")
    if any(label.startswith("xn--") for label in hostname.split(".")):
        score += 0.35
        reasons.append("문자가 변환된 Punycode 도메인을 사용합니다.")
    if parsed.username or parsed.password:
        score += 0.50
        reasons.append("URL에 사용자 정보가 포함되어 실제 주소를 숨길 수 있습니다.")
    if hostname in SHORTENERS:
        score += 0.40
        reasons.append("목적지를 바로 확인하기 어려운 단축 URL입니다.")

    labels = [label for label in hostname.split(".") if label]
    if len(labels) > 4:
        score += 0.25
        reasons.append("하위 도메인이 비정상적으로 많습니다.")
    if len(hostname) > 50:
        score += 0.20
        reasons.append("도메인 이름이 과도하게 깁니다.")
    if hostname.count("-") >= 4:
        score += 0.25
        reasons.append("도메인에 하이픈이 과도하게 많습니다.")
    if parsed.port is not None and parsed.port not in {80, 443}:
        score += 0.30
        reasons.append("일반적이지 않은 포트를 사용합니다.")
    if SUSPICIOUS_PATH_PATTERN.search(parsed.path):
        score += 0.30
        reasons.append("인증·로그인·환급·배송·결제와 관련된 경로가 있습니다.")

    return min(round(score, 4), 1.0), reasons


async def get_virustotal_report(
    url: str,
    *,
    api_key: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> ReputationResult:
    key = api_key if api_key is not None else os.getenv("VT_API_KEY", "")
    if not key.strip():
        return ReputationResult(status="NO_API_KEY")

    url_id = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").rstrip("=")
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            timeout=VT_TIMEOUT_SECONDS,
            follow_redirects=False,
        )
    try:
        response = await client.get(
            f"https://www.virustotal.com/api/v3/urls/{url_id}",
            headers={"x-apikey": key},
        )
        if response.status_code == 404:
            return ReputationResult(status="NOT_FOUND")
        if response.status_code == 429:
            return ReputationResult(status="RATE_LIMITED")
        if response.status_code != 200:
            return ReputationResult(status="ERROR")
        try:
            payload = response.json()
            stats = payload["data"]["attributes"]["last_analysis_stats"]
            return ReputationResult(
                status="FOUND",
                malicious=max(0, int(stats.get("malicious", 0))),
                suspicious=max(0, int(stats.get("suspicious", 0))),
            )
        except (KeyError, TypeError, ValueError):
            return ReputationResult(status="INVALID_RESPONSE")
    except httpx.TimeoutException:
        return ReputationResult(status="TIMEOUT")
    except httpx.HTTPError:
        return ReputationResult(status="ERROR")
    finally:
        if owns_client:
            await client.aclose()


async def analyze_url(
    url: str,
    *,
    api_key: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> UrlAnalysisResult:
    try:
        normalized = normalize_url(url)
        parsed = urlsplit(normalized)
    except ValueError:
        return UrlAnalysisResult(
            url=url,
            verdict="INVALID",
            riskScore=0.5,
            reasons=["URL 형식이 올바르지 않습니다."],
            reputation=ReputationResult(status="NOT_CHECKED"),
        )

    structure_score, reasons = inspect_url_structure(normalized)
    model_score, model_threshold = await run_in_threadpool(predict_url_risk, url)
    reputation = await get_virustotal_report(
        normalized,
        api_key=api_key,
        client=client,
    )
    score = structure_score
    domain_match = lookup_domain(normalized)
    is_official = domain_match is not None and domain_match["kind"] == "official"

    if reputation.malicious >= 2:
        verdict = "DANGEROUS"
        score = max(score, 0.95)
        reasons.append("복수의 보안 엔진이 악성 URL로 탐지했습니다.")
    elif reputation.malicious >= 1 or reputation.suspicious >= 1:
        verdict = "SUSPICIOUS"
        score = max(score, 0.70)
        reasons.append("일부 보안 엔진에서 의심 신호가 확인되었습니다.")
    elif structure_score >= URL_SUSPICIOUS_THRESHOLD:
        verdict = "SUSPICIOUS"
    elif is_official:
        verdict = "NO_KNOWN_THREAT"
        reasons.append("공식 도메인 화이트리스트에 등록되어 URL 모델의 의심 판정을 적용하지 않습니다.")
        if reputation.status != "FOUND":
            reasons.append(_reputation_reason(reputation.status))
    elif (
        model_score is not None
        and model_threshold is not None
        and model_score >= model_threshold
    ):
        verdict = "SUSPICIOUS"
        score = max(score, model_score)
        reasons.append("학습된 URL 패턴 모델에서 의심 신호가 확인되었습니다.")
    elif reputation.status == "FOUND":
        verdict = "NO_KNOWN_THREAT"
        reasons.append("현재 조회된 보안 평판에는 악성 탐지 이력이 없습니다.")
    else:
        verdict = "UNKNOWN"
        score = max(score, 0.40)
        reasons.append(_reputation_reason(reputation.status))

    return UrlAnalysisResult(
        url=normalized,
        hostname=parsed.hostname or "",
        verdict=verdict,
        riskScore=min(round(score, 4), 1.0),
        modelScore=None if model_score is None else min(round(model_score, 4), 1.0),
        reasons=_unique(reasons),
        reputation=reputation,
    )


def _reputation_reason(status: str) -> str:
    return {
        "NO_API_KEY": "보안 평판 API가 설정되지 않아 이 주소의 평판을 확인하지 못했습니다.",
        "NOT_FOUND": "기존 보안 평판 보고서가 없어 안전 여부를 확인할 수 없습니다.",
        "RATE_LIMITED": "보안 평판 조회 한도를 초과해 안전 여부를 확인하지 못했습니다.",
        "TIMEOUT": "보안 평판 조회 시간이 초과되어 안전 여부를 확인하지 못했습니다.",
        "INVALID_RESPONSE": "보안 평판 응답을 해석할 수 없어 안전 여부를 확인하지 못했습니다.",
    }.get(status, "보안 평판을 확인하지 못했습니다.")


def _is_ip_address(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
