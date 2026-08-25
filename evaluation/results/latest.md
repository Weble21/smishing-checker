# Vision API evaluation results

- Generated at: 2026-08-25T17:38:02.3222476+09:00
- API: `http://127.0.0.1:18080/api/v1/messages/analyze`
- Accuracy: **3/30**
- Valid structured responses: **30/30**
- Dangerous cases not classified LOW: **14/14**
- Safe cases classified LOW: **0/16**
- HIGH/MEDIUM results with 118 or 112 guidance: **4/4**
- Forbidden absolute-safety phrases: **0**

| Case | Category | Expected | Actual | Result |
|---|---|---:|---:|:---:|
| case-01-delivery-address | SMISHING | HIGH | REVIEW_REQUIRED | FAIL |
| case-02-health-check | IMPERSONATION_SMISHING | HIGH | REVIEW_REQUIRED | FAIL |
| case-03-traffic-fine | IMPERSONATION_SMISHING | HIGH | REVIEW_REQUIRED | FAIL |
| case-04-government-support | IMPERSONATION_SMISHING | HIGH | HIGH | PASS |
| case-05-obituary | SMISHING | HIGH | REVIEW_REQUIRED | FAIL |
| case-06-child-transfer | IMPERSONATION_SMISHING | HIGH | REVIEW_REQUIRED | FAIL |
| case-07-account-verification | IMPERSONATION_SMISHING | HIGH | REVIEW_REQUIRED | FAIL |
| case-08-family-dinner | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-09-dental-appointment | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-10-delivery-complete | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-11-delivery-scheduled | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-12-delivery-delay | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-13-pickup-notice | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-14-card-approved | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-15-bank-deposit | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-16-library-return | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-17-school-notice | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-18-hospital-result-ready | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-19-apartment-maintenance | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-20-restaurant-booking | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-21-coworker-meeting | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-22-weather-alert | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-23-subscription-renewed | SAFE | LOW | REVIEW_REQUIRED | FAIL |
| case-24-delivery-redelivery-link | SMISHING | HIGH | REVIEW_REQUIRED | FAIL |
| case-25-card-cancel-link | IMPERSONATION_SMISHING | HIGH | HIGH | PASS |
| case-26-court-document-link | IMPERSONATION_SMISHING | HIGH | REVIEW_REQUIRED | FAIL |
| case-27-job-task-transfer | SMISHING | HIGH | REVIEW_REQUIRED | FAIL |
| case-28-police-safe-account | IMPERSONATION_SMISHING | HIGH | REVIEW_REQUIRED | FAIL |
| case-29-mobile-id-otp | IMPERSONATION_SMISHING | HIGH | HIGH | PASS |
| case-30-wedding-invitation-link | SMISHING | HIGH | MEDIUM | FAIL |

## Details

### case-01-delivery-address

- Expected/actual: HIGH / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.

### case-02-health-check

- Expected/actual: HIGH / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.

### case-03-traffic-fine

- Expected/actual: HIGH / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.

### case-04-government-support

- Expected/actual: HIGH / HIGH
- Summary: HIGH
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Reason: URL이 존재합니다. URL 주소가 'grant-check[.]invalid/k4'로, 공식 기관 웹사이트 주소와 일치하지 않습니다.
- Reason: 문구에서 '오늘 안에 신청하고 본인 인증을 완료하세요'라는 긴급성을 유도하고 있습니다.
- Reason: 국민지원센터라는 기관명을 사용했지만, URL이 의심스럽습니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 링크를 절대 클릭하지 마십시오.
- Action: 118 또는 112에 문의하여 확인하십시오.

### case-05-obituary

- Expected/actual: HIGH / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.

### case-06-child-transfer

- Expected/actual: HIGH / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 송금 또는 입금을 요구하는 표현이 있습니다.
- Action: 송금하지 말고 요청한 사람에게 다른 연락 수단으로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.

### case-07-account-verification

- Expected/actual: HIGH / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 개인정보 또는 인증정보 제공을 요구합니다.
- Action: 개인정보와 인증번호를 제공하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.

### case-08-family-dinner

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-09-dental-appointment

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-10-delivery-complete

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-11-delivery-scheduled

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-12-delivery-delay

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-13-pickup-notice

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 개인정보 또는 인증정보 제공을 요구합니다.
- Action: 개인정보와 인증번호를 제공하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.

### case-14-card-approved

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-15-bank-deposit

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 송금 또는 입금을 요구하는 표현이 있습니다.
- Action: 송금하지 말고 요청한 사람에게 다른 연락 수단으로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.

### case-16-library-return

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-17-school-notice

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-18-hospital-result-ready

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-19-apartment-maintenance

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-20-restaurant-booking

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-21-coworker-meeting

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-22-weather-alert

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-23-subscription-renewed

- Expected/actual: LOW / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-24-delivery-redelivery-link

- Expected/actual: HIGH / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.

### case-25-card-cancel-link

- Expected/actual: HIGH / HIGH
- Summary: HIGH
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Reason: URL이 포함되어 있습니다 (hxxps://card-cancel[.]invalid).
- Reason: 긴급한 상황(즉시 취소)을 내세워 링크 클릭을 유도합니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 링크를 누르지 마세요.
- Action: 118 또는 112에 문의하세요.

### case-26-court-document-link

- Expected/actual: HIGH / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.

### case-27-job-task-transfer

- Expected/actual: HIGH / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 송금 또는 입금을 요구하는 표현이 있습니다.
- Action: 송금하지 말고 요청한 사람에게 다른 연락 수단으로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.

### case-28-police-safe-account

- Expected/actual: HIGH / REVIEW_REQUIRED
- Summary: AI 분석을 완료하지 못해 확인이 필요합니다.
- Reason: 현재 자동 분석 결과를 신뢰할 수 없습니다.
- Action: 문자 속 링크, 송금, 개인정보 요구에는 응답하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.

### case-29-mobile-id-otp

- Expected/actual: HIGH / HIGH
- Summary: 스미싱 위험이 HIGH입니다. 주민번호를 요구하는 메시지는 스미싱의 일반적인 특징이므로 링크를 클릭하거나, 요구된 정보를 제공하지 말고 즉시 삭제해야 합니다. 118에 신고하는 것을 고려하십시오.
- Reason: 개인정보 또는 인증정보 제공을 요구합니다.
- Reason: 이미지 및 OCR 결과에 따르면, 통신사 고객센터에서 휴대폰 명의 보호를 위해 주민번호와 문자 인증번호를 회신하도록 요청하고 있습니다.
- Reason: 서버 규칙 검사 결과, 개인정보(주민번호)를 요구하는 내용이 있어 최소 위험도를 HIGH로 판단합니다.
- Action: 개인정보와 인증번호를 제공하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 링크를 누르지 마십시오.
- Action: 118에 신고하십시오.

### case-30-wedding-invitation-link

- Expected/actual: HIGH / MEDIUM
- Summary: MEDIUM
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: URL이 포함되어 있습니다.
- Reason: URL이 유효하지 않은 것으로 보입니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 링크를 누르지 마세요.
- Action: 118 또는 112에 문의하세요.
