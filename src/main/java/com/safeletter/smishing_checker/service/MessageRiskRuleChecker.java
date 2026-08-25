package com.safeletter.smishing_checker.service;

import com.safeletter.smishing_checker.dto.RuleCheckResult;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

@Component
public class MessageRiskRuleChecker {

    private static final Pattern URL_PATTERN = Pattern.compile(
            "(?i)(?:https?://|hxxps?://|www\\.|[a-z0-9-]+(?:\\[\\.\\]|\\.)[a-z]{2,})(?:\\S*)?"
    );
    private static final Pattern TRANSFER_REQUEST_PATTERN = Pattern.compile(
            "(?:송금|입금|이체|납부)\\s*(?:해\\s*줘|해\\s*주세요|해주세요|하세요|"
                    + "해라|바랍니다|필요(?:합니다)?|요청(?:합니다)?)|"
                    + "보내\\s*(?:줘|주세요|세요|주시기\\s*바랍니다)"
    );
    private static final Pattern PERSONAL_INFORMATION_PATTERN = Pattern.compile(
            "주민(?:등록)?번호|비밀번호|인증번호|OTP|보안카드|카드번호|"
                    + "신분증|계정정보|개인정보",
            Pattern.CASE_INSENSITIVE
    );
    private static final Pattern INFORMATION_REQUEST_PATTERN = Pattern.compile(
            "입력|회신|알려|보내|제출|등록|인증|제공|전달|확인해\\s*주"
    );
    private static final Pattern NEGATED_INFORMATION_REQUEST_PATTERN = Pattern.compile(
            "(?:입력|회신|제출|등록|인증|제공|전달)(?:은|는|할)?\\s*"
                    + "(?:필요하지\\s*않|필요\\s*없|하지\\s*마|불필요)|"
                    + "(?:입력|회신|제출|등록|인증|제공|전달)하지\\s*않아도"
    );
    private static final Pattern URGENCY_PATTERN = Pattern.compile(
            "오늘|즉시|긴급|기한|정지|제한|보류|가산금|미납|"
                    + "대상자|선정|마감"
    );
    private static final Pattern IMPERSONATION_PATTERN = Pattern.compile(
            "택배|건강보험|교통민원|경찰|검찰|국세청|정부|지원금|"
                    + "은행|카드|금융|자녀|엄마|아빠|부고|장례식|청첩장|결혼"
    );

    public RuleCheckResult check(String message) {
        String text = message == null ? "" : message;
        boolean hasUrl = URL_PATTERN.matcher(text).find();
        boolean hasTransferRequest = TRANSFER_REQUEST_PATTERN.matcher(text).find();
        boolean requestsPersonalInformation = requestsPersonalInformation(text);
        boolean hasUrgency = URGENCY_PATTERN.matcher(text).find();
        boolean hasImpersonation = IMPERSONATION_PATTERN.matcher(text).find();

        List<String> reasons = new ArrayList<>();
        List<String> actions = new ArrayList<>();
        String minimumRiskLevel = "NONE";

        if (hasUrl) {
            minimumRiskLevel = "MEDIUM";
            reasons.add("문자에 URL이 포함되어 있습니다.");
            actions.add("문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.");
        }

        if (hasTransferRequest) {
            minimumRiskLevel = "HIGH";
            reasons.add("송금 또는 입금을 요구하는 표현이 있습니다.");
            actions.add("송금하지 말고 요청한 사람에게 다른 연락 수단으로 확인하세요.");
        }

        if (requestsPersonalInformation) {
            minimumRiskLevel = "HIGH";
            reasons.add("개인정보 또는 인증정보 제공을 요구합니다.");
            actions.add("개인정보와 인증번호를 제공하지 마세요.");
        }

        if (hasUrl && (hasUrgency || hasImpersonation)) {
            minimumRiskLevel = "HIGH";
            reasons.add("기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.");
        }

        if ("HIGH".equals(minimumRiskLevel)) {
            actions.add("의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.");
        }

        return new RuleCheckResult(minimumRiskLevel, reasons, actions);
    }

    private boolean requestsPersonalInformation(String text) {
        String[] clauses = text.split("[.!?\\n]|(?:다\\s*,)|(?:며\\s*)");
        for (String clause : clauses) {
            boolean hasSensitiveTerm = PERSONAL_INFORMATION_PATTERN
                    .matcher(clause)
                    .find();
            boolean hasRequest = INFORMATION_REQUEST_PATTERN
                    .matcher(clause)
                    .find();
            boolean isNegated = NEGATED_INFORMATION_REQUEST_PATTERN
                    .matcher(clause)
                    .find();
            if (hasSensitiveTerm && hasRequest && !isNegated) {
                return true;
            }
        }
        return false;
    }
}
