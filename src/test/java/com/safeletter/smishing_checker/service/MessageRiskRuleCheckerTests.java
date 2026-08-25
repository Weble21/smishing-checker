package com.safeletter.smishing_checker.service;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MessageRiskRuleCheckerTests {

    private final MessageRiskRuleChecker checker = new MessageRiskRuleChecker();

    @Test
    void marksImpersonationUrlAsHighRisk() {
        var result = checker.check(
                "OO택배 주소 불명으로 배송이 보류되었습니다. "
                        + "hxxps://delivery-check[.]invalid/a7"
        );

        assertEquals("HIGH", result.minimumRiskLevel());
        assertTrue(result.reasons().stream().anyMatch(
                reason -> reason.contains("URL")
        ));
    }

    @Test
    void marksTransferRequestAsHighRisk() {
        var result = checker.check("계좌로 48만원만 먼저 보내줘.");

        assertEquals("HIGH", result.minimumRiskLevel());
    }

    @Test
    void marksPersonalInformationRequestAsHighRisk() {
        var result = checker.check("주민번호 앞자리와 인증번호를 회신해 주세요.");

        assertEquals("HIGH", result.minimumRiskLevel());
    }

    @Test
    void leavesOrdinaryMessageWithoutRiskFloor() {
        var result = checker.check(
                "오늘 수업 끝나고 6시쯤 집에 도착해. 저녁 같이 먹자."
        );

        assertEquals("NONE", result.minimumRiskLevel());
    }

    @Test
    void doesNotApplyDeferredAppInstallationRule() {
        var result = checker.check("새 보안 앱을 설치해 주세요.");

        assertEquals("NONE", result.minimumRiskLevel());
    }
}
