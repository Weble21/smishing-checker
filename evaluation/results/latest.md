# Vision API evaluation results

- Generated at: 2026-08-25T14:06:23.1870836+09:00
- API: `http://127.0.0.1:18080/api/v1/messages/analyze`
- Accuracy: **10/10**
- Valid structured responses: **10/10**
- Dangerous cases not classified LOW: **7/7**
- Safe cases classified LOW: **3/3**
- HIGH results with 118 or 112 guidance: **7/7**
- Forbidden absolute-safety phrases: **0**

| Case | Category | Expected | Actual | Result |
|---|---|---:|---:|:---:|
| case-01-delivery-address | SMISHING | HIGH | HIGH | PASS |
| case-02-health-check | IMPERSONATION_SMISHING | HIGH | HIGH | PASS |
| case-03-traffic-fine | IMPERSONATION_SMISHING | HIGH | HIGH | PASS |
| case-04-government-support | IMPERSONATION_SMISHING | HIGH | HIGH | PASS |
| case-05-obituary | SMISHING | HIGH | HIGH | PASS |
| case-06-child-transfer | IMPERSONATION_SMISHING | HIGH | HIGH | PASS |
| case-07-account-verification | IMPERSONATION_SMISHING | HIGH | HIGH | PASS |
| case-08-family-dinner | SAFE | LOW | LOW | PASS |
| case-09-dental-appointment | SAFE | LOW | LOW | PASS |
| case-10-delivery-complete | SAFE | LOW | LOW | PASS |

## Details

### case-01-delivery-address

- Expected/actual: HIGH / HIGH
- Summary: 이 메시지는 스미싱 위험을 나타냅니다. URL이 의심스럽고, 배송 관련 내용으로 위장하여 링크 클릭을 유도하고 있습니다. 'oo택배'라는 기관을 사칭했을 가능성이 높습니다.
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Reason: URL이 'delivery-check[.]invalid'로 되어 있어 정상적인 배송 확인 페이지가 아닐 가능성이 높습니다.
- Reason: 긴급한 상황(배송 보류)을 언급하며 즉각적인 조치를 요구하여 링크 클릭을 유도하고 있습니다.
- Reason: 기관(oo택배)을 사칭하여 사용자를 속이려 할 수 있습니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 링크를 절대 클릭하지 마십시오.
- Action: 118 또는 112에 전화하여 스미싱 피해를 신고하고 도움을 받으십시오.

### case-02-health-check

- Expected/actual: HIGH / HIGH
- Summary: 이 메시지는 건강보험공단에서 발송되었다고 하지만, URL이 `hxxps://nh-check[.]invalid/r2`로 정상적인 건강검진 확인 페이지가 아닌 가짜 URL을 포함하고 있습니다. 기관을 사칭하여 링크 클릭을 유도하는 스미싱 의심 사례입니다.
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Reason: URL이 가짜 주소로 되어 있습니다. (hxxps://nh-check[.]invalid/r2)
- Reason: 건강검진 통보라는 긴급한 상황을 이용하여 링크 클릭을 유도합니다.
- Reason: 기관(건강보험공단)을 사칭하는 것으로 보입니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 절대로 링크를 클릭하지 마십시오.
- Action: 118 또는 112에 전화하여 스미싱 신고를 하십시오.

### case-03-traffic-fine

- Expected/actual: HIGH / HIGH
- Summary: 스미싱 의심 사례입니다. '교통민원24'라는 기관을 사칭하여 미납 과태료를 알리고, 링크 클릭을 유도하고 있습니다. URL이 'efine-check[.]invalid/p9'로 되어 있으며, 이는 스미싱 공격에 사용되는 가짜 URL일 가능성이 높습니다. 긴급성을 강조하여 링크 클릭을 유도하는 점도 스미싱의 특징입니다.
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Reason: URL이 존재하지 않는 가짜 URL(hxxps://efine-check[.]invalid/p9)을 포함하고 있습니다.
- Reason: 미납 과태료를 언급하며 긴급한 상황을 조성하여 링크 클릭을 유도하고 있습니다.
- Reason: 기관(교통민원24)을 사칭하고 있습니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 절대 링크를 클릭하지 마십시오.
- Action: 118 또는 112에 전화하여 신고하고 도움을 받으십시오.

### case-04-government-support

- Expected/actual: HIGH / HIGH
- Summary: 스미싱 의심 사례입니다. 국민지원센터를 사칭하여 고유가 국민지원금 지급 대상자로 선정되었다는 내용과 함께 본인 인증 및 신청을 유도하고 있습니다. URL이 'hxxps://grant-check[.]invalid/k4'로 되어 있어 의심스럽습니다. 링크 클릭 시 악성코드 감염이나 개인정보 유출의 위험이 있으므로 절대 클릭하지 말고, 118 또는 112에 문의하여 확인해야 합니다.
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Reason: URL이 'hxxps://grant-check[.]invalid/k4'로 되어 있어 공식 웹사이트와 일치하지 않습니다.
- Reason: 국민지원센터를 사칭하여 긴급한 상황(고유가 국민지원금)을 조성하여 링크 클릭을 유도하고 있습니다.
- Reason: 본인 인증 및 신청을 요구하여 개인정보를 요구하려 시도하고 있습니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 링크 클릭 금지
- Action: 118 또는 112에 문의하여 확인

### case-05-obituary

- Expected/actual: HIGH / HIGH
- Summary: 이 메시지는 아버지의 사망을 알리는 내용으로 보이지만, URL (hxxps://obituary[.]invalid/b5)이 의심스럽습니다. URL이 실제 장례식장 웹사이트가 아닌 스미싱 사이트로 위장했을 가능성이 높습니다. 긴급한 상황을 이용하여 링크 클릭을 유도하는 전형적인 스미싱 수법입니다.
- Reason: 문자에 URL이 포함되어 있습니다.
- Reason: 기관·지인 사칭 또는 긴급한 상황을 내세워 링크 클릭을 유도합니다.
- Reason: URL이 'obituary[.]invalid'로 되어 있어 공식적인 장례식장 웹사이트일 가능성이 낮습니다.
- Reason: 긴급한 상황(아버지의 사망)을 언급하여 링크 클릭을 유도하고 있습니다.
- Reason: 서버 규칙 검사에서 최소 위험도를 HIGH로 판단했습니다.
- Action: 문자 속 링크를 누르지 말고 공식 앱이나 대표번호로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 절대 링크를 클릭하지 마십시오.
- Action: 118 또는 112에 전화하여 스미싱 신고를 하십시오.

### case-06-child-transfer

- Expected/actual: HIGH / HIGH
- Summary: 스미싱 의심 사례입니다. 딸이 친구 번호로 보낸 문자 메시지를 받았지만, 수리비 명목으로 급하게 돈을 송금하라는 내용입니다. 계좌 정보(은행, 계좌번호, 이름)가 제시되어 있어 스미싱 가능성이 매우 높습니다.
- Reason: 송금 또는 입금을 요구하는 표현이 있습니다.
- Reason: 송금 요구: ‘48만 원만 먼저 보내줘’라는 표현이 명확하게 송금을 요구하고 있습니다.
- Reason: 긴급성 유도: ‘수리비가 급한데’라는 표현으로 긴급성을 유도하여 즉각적인 행동을 유도하고 있습니다.
- Reason: 낯선 계좌 요구: 친구 번호로 보낸 메시지라고 하지만, 실제로는 스미싱 공격자가 제공하는 계좌로 돈을 송금하도록 유도하는 것입니다.
- Action: 송금하지 말고 요청한 사람에게 다른 연락 수단으로 확인하세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 링크 클릭 금지
- Action: 118 또는 112에 신고하여 도움 요청

### case-07-account-verification

- Expected/actual: HIGH / HIGH
- Summary: 이 메시지는 은행 보안센터를 사칭하여 계정 제한 해제를 위해 주민등록번호 앞자리와 인증번호를 요구하고 있습니다. 이는 스미싱의 대표적인 수법으로, 개인정보 유출 및 금융 피해로 이어질 수 있는 매우 위험한 상황입니다.
- Reason: 개인정보 또는 인증정보 제공을 요구합니다.
- Reason: 은행 보안센터를 사칭하고 있습니다.
- Reason: 계정 제한 해제를 위해 주민등록번호 앞자리와 인증번호를 요구하고 있습니다.
- Reason: 개인정보(주민등록번호)를 요구하는 것은 스미싱의 특징적인 행동입니다.
- Action: 개인정보와 인증번호를 제공하지 마세요.
- Action: 의심되면 국번 없이 118 또는 긴급한 피해 상황은 112에 문의하세요.
- Action: 절대로 링크를 클릭하지 마세요.
- Action: 118 또는 112에 전화하여 신고하고 도움을 요청하세요.

### case-08-family-dinner

- Expected/actual: LOW / LOW
- Summary: 스미싱 위험은 없습니다. 아들이 엄마에게 집에 도착 시간과 저녁 식사에 대한 메시지를 보낸 것으로 보입니다. 송금 요구, 개인정보 요구, 긴급성 유도 등의 스미싱 특징이 발견되지 않았습니다. 하지만, 메시지 내용이 일반적인 가족 간의 대화이므로 주의가 필요합니다.
- Reason: 메시지 내용이 가족 간의 일상적인 대화입니다.
- Reason: 송금, 개인정보 요구, 긴급성 유도 등의 스미싱 특징이 없습니다.
- Reason: 서버 규칙 검사에서 최소 위험도를 나타냅니다.
- Action: 링크를 누르지 마세요.
- Action: 필요하다면 118 또는 112에 문의하여 확인해 보세요.

### case-09-dental-appointment

- Expected/actual: LOW / LOW
- Summary: 스미싱 위험 가능성은 낮습니다. 하지만 주의가 필요합니다.
- Reason: 발신자는 'OO치과'이며, 정기 검진 예약 안내 메시지입니다.
- Reason: 메시지 내용에는 송금 요구, 개인정보 요구, 긴급성 유도 등의 스미싱 특징이 보이지 않습니다.
- Reason: 메시지 말미에 '변경이 필요하면 병원 대표번호로 직접 전화해 주세요'라는 문구가 있어, 사용자가 직접 병원에 연락하여 확인하도록 유도하고 있습니다.
- Action: 링크를 클릭하지 마십시오.
- Action: 의심스러운 경우, 병원 대표번호로 직접 전화하여 예약 여부를 확인하십시오.
- Action: 118 또는 112에 문의하여 도움을 받을 수 있습니다.

### case-10-delivery-complete

- Expected/actual: LOW / LOW
- Summary: 스미싱 위험은 낮습니다. 하지만 주의가 필요합니다.
- Reason: 문자 메시지는 상품 배송 완료를 알리고 있습니다.
- Reason: 추가 사항 확인을 요청하고 있지만, 특정 링크를 클릭하거나 개인 정보를 요구하지 않습니다.
- Reason: 서버 규칙 검사 결과 위험 신호는 발견되지 않았습니다.
- Action: 링크를 클릭하지 마세요.
- Action: 메시지 발신자(OO택배)의 공식 앱에서 주문 내역을 확인하는 것이 안전합니다.
