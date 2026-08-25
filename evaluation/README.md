# 스미싱 이미지 평가 세트

`labels.json`의 문자 내용을 휴대폰 문자 화면처럼 렌더링한 PNG 30장과 기대 위험도를 한 쌍으로 관리합니다. 정상 대조군에는 택배 도착 예정·배송 지연처럼 사칭으로 오인하기 쉬운 알림을 포함합니다.

- `SMISHING`: 택배·부고처럼 일상 소재로 악성 URL 클릭을 유도하는 사례
- `IMPERSONATION_SMISHING`: 공공기관·금융기관·가족을 사칭해 URL, 송금, 개인정보 또는 인증번호를 요구하는 사례
- `SAFE`: 링크·송금·개인정보 요구가 없는 합성 정상 대조군

공식 사례는 KISA가 공개한 유형과 문구를 짧게 재구성했습니다. 실제 악성 주소와 개인정보는 포함하지 않았으며 모든 의심 URL은 예약 도메인 `.invalid`와 `hxxps` 표기로 비활성화했습니다. 따라서 이 데이터는 실제 악성 URL 평판 검사가 아니라 화면 OCR과 메시지 위험 신호 판별을 평가합니다.

## 실행

프로젝트 루트에서 다음 순서로 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/generate-evaluation-images.ps1
powershell -ExecutionPolicy Bypass -File scripts/run-vision-evaluation.ps1 -BaseUrl http://127.0.0.1:18080
```

두 번째 명령을 실행하기 전에 애플리케이션을 같은 주소에서 실행해야 합니다. 결과는 `evaluation/results/latest.json`과 `evaluation/results/latest.md`에 저장됩니다.

평가기의 기본값은 사례 사이에 1.5초를 기다리고, 일시적인 요청 제한·타임아웃·서버 오류·비정상 AI 응답을 최대 3번 시도합니다. 필요하면 다음처럼 조정할 수 있습니다.

```powershell
powershell -ExecutionPolicy Bypass `
  -File scripts/run-vision-evaluation.ps1 `
  -BaseUrl http://127.0.0.1:18080 `
  -MaxAttempts 3 `
  -RequestDelayMilliseconds 2000
```

보고서는 전체 일치율과 별도로 AI 완료율, 완료된 AI 응답만의 정확도, AI/OCR 실패 원인과 재시도 횟수를 기록합니다. 판정 성공 기준은 기대 위험도와 API의 `riskLevel`이 정확히 같은지 여부입니다. 이유 문구는 모델마다 표현이 달라 자동 채점하지 않고 결과 보고서에서 사람이 검토합니다.
