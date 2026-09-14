---
language:
- ko
license: cc-by-nc-4.0
tags:
- security
- smishing
- phishing
- synthetic-data
- siem
- detection-engineering
- mitre-attack
- korean
task_categories:
- text-classification
size_categories:
- n<1K
---

# KR-MOB-SMISHING v1

**한국형 모바일 스미싱 합성 데이터셋 — SIEM 상관분석 훈련용**

Korean Mobile Smishing Synthetic Dataset for SIEM Correlation Training

---

## 이 데이터셋을 만든 이유

2024년 한국의 스미싱 피해 건수는 22만 건을 넘었습니다. 전년 대비 290% 급증. 피해 금액은 1조 4천억 원에 달합니다.

택배 문자를 눌렀을 뿐인 부모님, 은행 보안 알림을 믿은 직장인, 면접 결과 문자에 속은 취업준비생. 피해자는 늘 평범한 사람들입니다.

그런데 이 공격을 막아야 할 보안팀과 AI 모델은 역설적인 상황에 놓여 있습니다. 실제 스미싱 로그는 개인정보 보호 규정과 기업 보안 정책에 묶여 공유가 불가능하고, 방어자들은 데이터 없이 직감에 의존해 탐지 규칙을 만들어야 합니다.

이 악순환을 끊기 위해 KR-MOB-SMISHING을 만들었습니다.

한국 모바일 네트워크에서 실제로 발생하는 공격 패턴을 그대로 재현하되, 개인정보 위험은 제로, 실제 피해 가능성도 제로인 합성 데이터셋입니다. SIEM 상관분석 규칙 개발, 보안 분석가 훈련, 탐지 엔지니어링 벤치마킹을 위해 설계되었습니다.

이 데이터로 훈련한 단 한 명의 보안 분석가가, 단 한 건의 실제 스미싱을 더 빨리 잡아낸다면 — 이 데이터셋을 만든 보람이 있습니다.

---

## Why This Dataset Exists

In 2024, South Korea recorded over 220,000 smishing cases — a 290% surge from the previous year. Victims lost a combined ₩1.4 trillion, and the damage falls hardest on ordinary people: a parent who clicks a fake parcel link, an office worker who trusts a spoofed bank alert, a job seeker who opens a fraudulent interview notice.

Yet the security teams and AI models tasked with stopping these attacks face a paradox: real smishing logs are locked behind privacy regulations and corporate silos, leaving defenders to build detection rules on intuition rather than data.

We built KR-MOB-SMISHING to break that cycle.

This is a purpose-built synthetic dataset of 100 mobile smishing/phishing incidents designed for SIEM correlation rule development, security analyst training, and detection engineering benchmarking. Every incident mirrors the attack patterns actually seen on Korean mobile networks — but with zero privacy risk, zero real-world harm, and full transparency.

If one SOC analyst catches one real smishing campaign faster because they trained on this data, it was worth building.

---

## Dataset Overview

| 항목 | 수치 |
|---|---|
| Dataset Name | KR-MOB-SMISHING v1 |
| Total Incidents | 100 |
| Avg Events / Incident | 10.0 |
| Avg Duration | 81.8 min |
| Validation PASS Rate | 100% (100/100) |
| Format | JSON (1 file per incident) |
| Language | Korean (한국어) |
| License | CC BY-NC 4.0 |

---

## Key Features

- 3가지 케이스 유형: malicious(킬체인 완성), benign_lookalike(부분 공격, 사용자 중단), benign(정상 활동)
- 한국 실정 반영 10대 스미싱 테마
- 5개 SIEM 상관분석 규칙 + 사전 검증된 fire/no-fire 판정
- 12종 이벤트 타입 + MITRE ATT&CK for Mobile 매핑
- Android/iOS 듀얼 플랫폼 커버리지
- 3단계 난이도 (HIGH 48%, MEDIUM 42%, LOW 10%)
- RFC 2606 안전 도메인(.example), TEST-NET IP, 마스킹 전화번호
- 모든 SMS에 [TRAINING] 워터마크 포함

---

## Case Type Distribution

| Case Type | Count | Ratio | Description |
|---|---|---|---|
| malicious | 40 | 40% | 킬체인 완성, 피해 발생 |
| benign_lookalike | 31 | 31% | 공격 존재하나 사용자 중단 |
| benign | 29 | 29% | 정상 활동, 공격 없음 |

---

## Difficulty Distribution

| Tier | Count | Ratio | Description |
|---|---|---|---|
| DT-HIGH | 48 | 48% | 다단계 리디렉션, 경고 우회, 금융 사기 |
| DT-MEDIUM | 42 | 42% | 중간 복잡도 공격 체인 |
| DT-LOW | 10 | 10% | 단순 패턴, 초급 훈련용 |

---

## Platform Coverage

| Platform | Appearances | Ratio |
|---|---|---|
| Android | 57 | 50.4% |
| iOS | 56 | 49.6% |

---

## Theme Coverage (10 Scenarios)

| # | Theme | Count |
|---|---|---|
| 1 | 계정 보안 경고 사칭 | 16 |
| 2 | 가족/지인 사칭 긴급 송금 | 12 |
| 3 | 채용/면접 결과 사칭 | 12 |
| 4 | 인증서 갱신/만료 사칭 | 12 |
| 5 | 통신사 요금/데이터 사칭 | 9 |
| 6 | 택배/배송 실패 사칭 | 9 |
| 7 | 결제/승인 확인 사칭 | 9 |
| 8 | 모바일 금융앱 업데이트 사칭 | 7 |
| 9 | 정부지원금/환급금 사칭 | 7 |
| 10 | 공공기관 과태료/세금 사칭 | 6 |

---

## Correlation Rule Benchmark

| Rule | Fires=True | Fires=False | Fire Rate | Window |
|---|---|---|---|---|
| SMISH_REDIRECT_CHAIN | 43 | 57 | 43% | 180s |
| SENSITIVE_FORM_SEQUENCE | 39 | 61 | 39% | 600s |
| POST_LURE_FINANCIAL_RISK_SIGNAL | 30 | 70 | 30% | 900s |
| PHISH_WARNING_BYPASS | 20 | 80 | 20% | standalone |
| PLATFORM_DIVERGENCE | 7 | 93 | 7% | 900s |

---

## Event Type Distribution

| Event Type | Count | Ratio | Category |
|---|---|---|---|
| background.normal_traffic | 407 | 39.3% | noise |
| dns.query | 129 | 12.5% | network |
| sms.received | 126 | 12.2% | messaging |
| http.request | 91 | 8.8% | network |
| http.redirect | 59 | 5.7% | network |
| web.risk_warning | 56 | 5.4% | browser_security |
| ios.web.behavior | 54 | 5.2% | browser_security |
| auth.step_up_challenge | 47 | 4.5% | identity |
| android.web_submission.blocked | 24 | 2.3% | endpoint |
| form.interaction | 20 | 1.9% | web_telemetry |
| bank.transfer_attempt_flagged | 17 | 1.6% | financial |
| device.compliance | 5 | 0.5% | endpoint |

---

## Safety & Compliance

| Check | Result |
|---|---|
| Domain TLD (.example only, RFC 2606) | PASS |
| IP Range (TEST-NET only) | PASS |
| Phone Number (masked only) | PASS |
| Brand Name / Logo | None (PASS) |
| [TRAINING] Watermark | All SMS (PASS) |
| Label Consistency (must_fire = malicious count) | PASS |

---

## File Structure

KR-MOB-SMISHING-v1/ ├── README.md └── incidents/ ├── inc-MOB-MAL-001.json ├── inc-MOB-BEN-002.json ├── inc-MOB-BEN-003.json └── ... (100 files)


Each JSON file is a self-contained incident with event stream, rule fire verification, scaling template, persona, and behavioral model.

---

## Use Cases

- SOC 분석가 교육 및 역량 평가
- SIEM 상관분석 규칙 개발 및 튜닝
- 탐지 엔지니어링 CI/CD 파이프라인 테스트
- 퍼플팀(Purple Team) 훈련 시나리오
- 피싱/스미싱 탐지 학술 연구
- 보안 제품 벤치마킹

---

## License

This dataset is licensed under **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**.

You are free to share and adapt this dataset for non-commercial purposes with appropriate attribution. For commercial use, please contact the author.

https://creativecommons.org/licenses/by-nc/4.0/

---

## Citation

@dataset{kr_mob_smishing_v1_2026, title={KR-MOB-SMISHING v1: Korean Mobile Smishing Synthetic Dataset}, year={2026}, license={CC BY-NC 4.0}, language={Korean} }


---

## Contact

For commercial licensing, questions, or feedback, please open an issue or contact the author.
📧 senimanyc@gmail.com

스미싱 피해는 계속 늘고 있습니다. 훈련 데이터는 턱없이 부족합니다. 이 데이터셋이 그 간극을 조금이라도 줄이는 데 기여하길 바랍니다.