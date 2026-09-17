from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import urlsplit

from schemas import DynamicAnalysisResponse, DynamicAssessment


EXECUTABLE_SUFFIXES = {".apk", ".exe", ".msi", ".dmg", ".pkg", ".bat", ".cmd", ".scr"}


def assess(result: DynamicAnalysisResponse) -> DynamicAssessment:
    if result.status != "COMPLETED":
        return DynamicAssessment(
            verdict="INCONCLUSIVE",
            reasons=["동적 분석을 완료하지 못했습니다."],
        )

    reasons: list[str] = []
    dangerous = False
    suspicious = False
    for download in result.downloads:
        suffix = PurePosixPath(download.suggestedFilename.lower()).suffix
        if suffix in EXECUTABLE_SUFFIXES:
            dangerous = True
            reasons.append(f"실행 가능한 파일({suffix}) 다운로드를 시도했습니다.")

    final_host = (urlsplit(result.finalUrl or result.requestedUrl).hostname or "").lower()
    for form in result.forms:
        if not form.sensitiveFields:
            continue
        suspicious = True
        reasons.append("비밀번호·인증번호·결제정보로 보이는 입력 항목이 있습니다.")
        action_host = (urlsplit(form.action).hostname or "").lower()
        if action_host and final_host and action_host != final_host:
            reasons.append("민감정보 입력 폼이 현재 페이지와 다른 호스트로 전송됩니다.")

    if dangerous:
        return DynamicAssessment(verdict="DANGEROUS", reasons=list(dict.fromkeys(reasons)))
    if suspicious:
        return DynamicAssessment(verdict="SUSPICIOUS", reasons=list(dict.fromkeys(reasons)))
    return DynamicAssessment(
        verdict="NO_OBSERVED_THREAT",
        reasons=["제한된 관찰 시간 동안 실행 파일 다운로드나 민감정보 입력 폼을 확인하지 못했습니다."],
    )

