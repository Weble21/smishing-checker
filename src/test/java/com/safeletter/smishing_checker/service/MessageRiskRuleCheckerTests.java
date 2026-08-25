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
    void marksSafeAccountTransferRequestAsHighRisk() {
        var result = checker.check(
                "경찰청 수사관입니다. 자산 보호를 위해 안전계좌로 전액 이체하세요."
        );

        assertEquals("HIGH", result.minimumRiskLevel());
    }

    @Test
    void doesNotTreatCompletedDepositAsTransferRequest() {
        var result = checker.check(
                "홍길동님 계좌에 50,000원이 입금되었습니다. 회신할 필요가 없습니다."
        );

        assertEquals("NONE", result.minimumRiskLevel());
    }

    @Test
    void doesNotTreatNegatedPersonalInformationAsRequest() {
        var result = checker.check(
                "택배를 수령해 주세요. 결제나 개인정보 입력은 필요하지 않습니다."
        );

        assertEquals("NONE", result.minimumRiskLevel());
    }

    @Test
    void leavesOrdinaryMessageWithoutRiskFloor() {
        var result = checker.check(
                "오늘 수업 끝나고 6시쯤 집에 도착해. 저녁 같이 먹자."
        );

        assertEquals("NONE", result.minimumRiskLevel());
    }

    @Test
    void leavesRoutineDeliveryNoticeWithoutRiskFloor() {
        var result = checker.check(
                "OO택배 고객님의 상품이 오늘 오후 도착 예정입니다. "
                        + "배송 현황은 주문한 쇼핑몰 공식 앱에서 확인해 주세요."
        );

        assertEquals("NONE", result.minimumRiskLevel());
    }

    @Test
    void doesNotApplyDeferredAppInstallationRule() {
        var result = checker.check("새 보안 앱을 설치해 주세요.");

        assertEquals("NONE", result.minimumRiskLevel());
    }
}
