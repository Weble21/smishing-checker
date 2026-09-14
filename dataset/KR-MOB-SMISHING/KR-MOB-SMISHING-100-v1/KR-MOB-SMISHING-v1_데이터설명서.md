# KR-MOB-SMISHING v1 데이터 설명서

---

## 1. 데이터 개요

### 데이터 변경이력

| 버전 | 일자 | 변경내용 | 비고 |
|---|---|---|---|
| 1.0 | 2026-03-01 | 데이터 최종 개방 | 초기 배포 |

### 소개

한국형 모바일 스미싱/피싱/정보탈취 시나리오에 대한 SIEM 상관분석 훈련·평가용 합성 이벤트 스트림 데이터셋입니다. 실제 한국 모바일 네트워크에서 발생하는 스미싱 공격 패턴을 재현하되, 개인정보 위험 없이 안전하게 사용할 수 있도록 설계되었습니다.

### 구축목적

2024년 한국 스미싱 피해 22만 건(전년 대비 290% 증가), 피해 금액 1조 4천억 원에 대응하여 다음 목적으로 구축되었습니다:

1. SOC 보안 분석가의 스미싱 탐지 역량 훈련
2. SIEM 상관분석 규칙 개발 및 튜닝
3. 탐지 엔지니어링 CI/CD 파이프라인 테스트
4. 보안 제품 벤치마킹
5. 피싱/스미싱 탐지 학술 연구

### 구축방법

AI 기반 합성 데이터 생성 파이프라인(Gemini 3.0 + QualityValidator)으로 자체 제작. 10개 시드 시나리오 × 7개 변형 축의 조합으로 다양한 인시던트를 생성하고, 19개 항목 자동 검증을 통과한 건만 포함.

---

## 2. 데이터 구조표

| 항목 | 내용 |
|---|---|
| 데이터 영역 | 사이버보안 / 재난안전 |
| 데이터 유형 | 이벤트 스트림 (시계열 로그) |
| 데이터 형식 | JSON |
| 데이터 출처 | AI 합성 생성 (Gemini 3.0 + QualityValidator) |
| 라벨링 유형 | ground_truth, case_type, attack_stage, mitre_mobile, rule_fire_verification |
| 라벨링 형식 | JSON (인라인) |
| 데이터 활용 서비스 | SIEM 상관분석, SOC 훈련, 탐지 엔지니어링 |
| 데이터 구축년도 / 구축량 | 2026년 / 100건 (약 995 이벤트) |

---

## 3. 데이터 통계

### 3-1. 데이터 구축 규모

| 항목 | 구분 | 건수 | 비율(%) |
|---|---|---|---|
| **케이스 유형** | malicious | 40 | 40.0 |
| | benign_lookalike | 31 | 31.0 |
| | benign | 29 | 29.0 |
| | 합계 | 100 | 100.0 |
| **난이도** | DT-HIGH | 48 | 48.0 |
| | DT-MEDIUM | 42 | 42.0 |
| | DT-LOW | 10 | 10.0 |
| | 합계 | 100 | 100.0 |
| **플랫폼** | Android | 57 | 50.4 |
| | iOS | 56 | 49.6 |
| | 합계 (중복 포함) | 113 | 100.0 |

### 3-2. 테마 분포

| # | Theme | 건수 | 비율(%) |
|---|---|---|---|
| 1 | 계정 보안 경고 사칭 | 16 | 16.0 |
| 2 | 가족/지인 사칭 긴급 송금 | 12 | 12.0 |
| 3 | 채용/면접 결과 사칭 | 12 | 12.0 |
| 4 | 인증서 갱신/만료 사칭 | 12 | 12.0 |
| 5 | 통신사 요금/데이터 사칭 | 9 | 9.0 |
| 6 | 택배/배송 실패 사칭 | 9 | 9.0 |
| 7 | 결제/승인 확인 사칭 | 9 | 9.0 |
| 8 | 모바일 금융앱 업데이트 사칭 | 7 | 7.0 |
| 9 | 정부지원금/환급금 사칭 | 7 | 7.0 |
| 10 | 공공기관 과태료/세금 사칭 | 6 | 6.0 |
| | 합계 | 100* | 100.0 |

*일부 테마명 변형(4건)은 원본 테마로 분류

### 3-3. 상관분석 규칙 분포

| 규칙 | Fires=True | Fires=False | Fire Rate | Window |
|---|---|---|---|---|
| SMISH_REDIRECT_CHAIN | 43 | 57 | 43% | 180s |
| SENSITIVE_FORM_SEQUENCE | 39 | 61 | 39% | 600s |
| POST_LURE_FINANCIAL_RISK_SIGNAL | 30 | 70 | 30% | 900s |
| PHISH_WARNING_BYPASS | 20 | 80 | 20% | standalone |
| PLATFORM_DIVERGENCE | 7 | 93 | 7% | 900s |

### 3-4. 이벤트 타입 분포

| Event Type | 건수 | 비율(%) | Category |
|---|---|---|---|
| background.normal_traffic | 407 | 39.3 | noise |
| dns.query | 129 | 12.5 | network |
| sms.received | 126 | 12.2 | messaging |
| http.request | 91 | 8.8 | network |
| http.redirect | 59 | 5.7 | network |
| web.risk_warning | 56 | 5.4 | browser_security |
| ios.web.behavior | 54 | 5.2 | browser_security |
| auth.step_up_challenge | 47 | 4.5 | identity |
| android.web_submission.blocked | 24 | 2.3 | endpoint |
| form.interaction | 20 | 1.9 | web_telemetry |
| bank.transfer_attempt_flagged | 17 | 1.6 | financial |
| device.compliance | 5 | 0.5 | endpoint |
| 합계 | ~995 | 100.0 | 12종 |

---

## 4. 저작도구 설명

### 생성 파이프라인

| 구성요소 | 도구 | 역할 |
|---|---|---|
| 실행 환경 | Google Colab (Python 3) | 코드 실행 및 파일 관리 |
| 생성 엔진 | Gemini API | 시드+변형 조합 기반 인시던트 JSON 생성 |
| 검증기 | QualityValidator (자체 개발) | 19개 항목 자동 검증, PASS/FAIL 판정 |
| 패키징 | Python zipfile | 최종 파일 압축 및 배포 |

### 생성 프로세스

1. CELL 1: 환경 초기화 (API 키, 라이브러리)
2. CELL 2: 시드 카탈로그 10개 + 변형 축 7개 로드
3. CELL 3: 시드 × 변형 조합 자동 생성
4. CELL 4: 시스템 프롬프트 + 스키마/규칙 정의
5. CELL 5: API 호출 함수
6. CELL 6: QualityValidator (19개 항목 검증)
7. CELL 7: SyntheticDataPipeline (생성+검증 통합)
8. CELL 8: 배치 실행 + FAIL 자동 삭제 + 통계 + 다운로드

---

## 5. 어노테이션 포맷 및 데이터 구조

### 5-1. 인시던트 최상위 구조

| No | 항목명 | 타입 | 구분 | 설명 | 예시 |
|---|---|---|---|---|---|
| 1 | incident_id | string | 필수 | 인시던트 고유 식별자 | "inc-MOB-MAL-001" |
| 2 | case_type | string | 필수 | 케이스 유형 | "malicious" |
| 3 | theme | string | 필수 | 스미싱 테마 | "택배/배송 실패 사칭" |
| 4 | difficulty_tier | string | 필수 | 난이도 | "DT-HIGH" |
| 5 | timeline_profile | string | 필수 | 타임라인 프로파일 | "rapid_chain" |
| 6 | start_time | string | 필수 | 시작 시간 (RFC 3339) | "2025-07-30T13:14:22+09:00" |
| 7 | end_time | string | 필수 | 종료 시간 (RFC 3339) | "2025-07-30T13:28:45+09:00" |
| 8 | platform_coverage | array | 필수 | 플랫폼 목록 | ["Android", "iOS"] |
| 9 | minimum_log_sources_required | array | 필수 | 최소 로그 소스 | ["messaging", "network"] |
| 10 | full_log_sources_used | array | 필수 | 전체 로그 소스 | ["messaging", "network", "browser_security"] |
| 11 | noise_model_applied | object | 필수 | 노이즈 모델 설정 | {"profile": "standard_enterprise", "background_event_ratio": 0.545} |
| 12 | message_samples_used | array | 필수 | 스미싱 메시지 샘플 | [{"text": "[TRAINING] 택배...", ...}] |
| 13 | page_construction_detail_safe | object | 필수 | 페이지 구성 상세 | {"no_brand_copy": true, ...} |
| 14 | persona | object | 필수 | 사용자 페르소나 | {"user_id": "user-finance-092", ...} |
| 15 | behavioral_model_for_this_incident | object | 필수 | 행동 모델 설명 | {"scenario": "...", ...} |
| 16 | expected_rules | object | 필수 | 예상 규칙 판정 | {"must_fire": [...], ...} |
| 17 | event_stream | array | 필수 | 이벤트 스트림 배열 | [{...}, {...}] |
| 18 | event_stream_timeline_summary | object | 필수 | 타임라인 요약 | {"total_events": 11, ...} |
| 19 | rule_fire_verification | object | 필수 | 규칙 판정 검증 결과 | {"SMISH_REDIRECT_CHAIN": {...}, ...} |
| 20 | scaling_template | object | 필수 | 스케일링 템플릿 | {"to_reach_200_events": {...}} |

### 5-2. 이벤트 스트림 개별 이벤트 구조

| No | 항목명 | 타입 | 구분 | 설명 |
|---|---|---|---|---|
| 1 | event_id | string | 필수 | 이벤트 고유 ID (UUID4) |
| 2 | time | string | 필수 | 이벤트 시간 (RFC 3339 + timezone) |
| 3 | log_source | string | 필수 | 로그 소스 카테고리 |
| 4 | event_type | string | 필수 | 이벤트 타입 |
| 5 | severity | string | 필수 | 심각도 (LOW/MEDIUM/HIGH/CRITICAL) |
| 6 | entity | object | 필수 | 엔티티 정보 (user_id, device_id, platform 등) |
| 7 | network | object | 필수 | 네트워크 정보 (dst_domain, dst_ip 등) |
| 8 | object | object | 필수 | 이벤트별 상세 데이터 |
| 9 | correlation | object | 필수 | 상관분석 연결 정보 (incident_id 등) |
| 10 | label | object | 필수 | 라벨 (ground_truth, case_type, attack_stage 등) |
| 11 | original_source_hint | string | 필수 | 원본 로그 소스 힌트 |

### 5-3. 이벤트 타입 레지스트리

| event_type | category | 주요 object 필드 | 참여 규칙 |
|---|---|---|---|
| sms.received | messaging | sender_type, sender_id, contains_url, message_features | SMISH_REDIRECT_CHAIN |
| dns.query | network | qtype | SMISH_REDIRECT_CHAIN |
| http.request | network | user_initiated | SMISH_REDIRECT_CHAIN |
| http.redirect | network | redirect_hops_total, referrer_chain_domains_masked | SMISH_REDIRECT_CHAIN |
| web.risk_warning | browser_security | warning_type, ui_warning_shown, user_bypassed_warning | PHISH_WARNING_BYPASS |
| ios.web.behavior | browser_security | behavior.signal, dwell_time_ms | SENSITIVE_FORM_SEQUENCE, PLATFORM_DIVERGENCE |
| form.interaction | web_telemetry | form.risk_class, submission_attempted | SENSITIVE_FORM_SEQUENCE |
| android.web_submission.blocked | endpoint | block_reason, action | PLATFORM_DIVERGENCE |
| auth.step_up_challenge | identity | auth.method, auth.result | POST_LURE_FINANCIAL_RISK_SIGNAL |
| bank.transfer_attempt_flagged | financial | risk_decision, result | POST_LURE_FINANCIAL_RISK_SIGNAL |
| background.normal_traffic | noise | traffic_category (선택) | — |
| device.compliance | endpoint | posture, os_patch_level | — |

### 5-4. 상관분석 규칙 정의

| 규칙 | Weight | Window | Fire 조건 |
|---|---|---|---|
| SMISH_REDIRECT_CHAIN | 0.35 | 180s | SMS(contains_url+urgency) → DNS(domain_age≤3) → HTTP(redirect_hops≥2) |
| PHISH_WARNING_BYPASS | 0.20 | standalone | web.risk_warning(shown=true, bypassed=true) |
| SENSITIVE_FORM_SEQUENCE | 0.25 | 600s | prerequisite(SMISH or PHISH) → form/ios.web.behavior |
| PLATFORM_DIVERGENCE | 0.10 | 900s | Android blocked → iOS continued (cross-device) |
| POST_LURE_FINANCIAL_RISK_SIGNAL | 0.30 | 900s | prerequisite(SMISH) → MFA burst(≥3) or bank flag |

### 5-5. 라벨 체계

| 필드 | 값 | 설명 |
|---|---|---|
| ground_truth | benign | 정상 활동 |
| | suspicious | 공격 인프라와 간접 상호작용 |
| | malicious | 공격 인프라와 직접 상호작용 |
| case_type | benign | 공격 자체가 없음 |
| | benign_lookalike | 공격 존재하나 사용자 중단 |
| | malicious | 킬체인 완성 |
| attack_stage | MITRE ATT&CK 단계 | malicious 케이스 |
| | attempted_* | benign_lookalike 케이스 |
| | null | benign 케이스 |

---

## 6. 안전성 및 컴플라이언스

| 항목 | 규격 | 적용 결과 |
|---|---|---|
| 도메인 | .example TLD만 사용 (RFC 2606) | PASS |
| IP 주소 | TEST-NET 블록만 사용 (RFC 5737) | PASS |
| 전화번호 | 마스킹 가상번호만 사용 (010-0000-xxxx) | PASS |
| 브랜드/로고 | 미포함 | PASS |
| [TRAINING] 워터마크 | 모든 SMS에 포함 | PASS |
| 실제 개인정보 | 미포함 | PASS |

---

## 7. 구축 담당자

| 항목 | 내용 |
|---|---|
| 구축 방식 | 개인 프로젝트 |
| 담당자 이메일 | [senimanyc@gmail.com] |
| 라이선스 | CC BY-NC 4.0 |

---

## 8. 활용 가이드

### 8-1. SIEM 인제스트

각 JSON 파일의 event_stream 배열을 SIEM에 개별 이벤트로 인제스트합니다. correlation.incident_id로 동일 인시던트 이벤트를 그룹핑할 수 있습니다.

### 8-2. 탐지 규칙 테스트

rule_fire_verification 필드의 fires 값을 정답지로 사용합니다. SIEM에서 규칙을 구현한 후, 각 인시던트에 대해 규칙이 올바르게 fire/no-fire하는지 비교합니다.

### 8-3. 분석가 훈련

event_stream만 제공하고 case_type과 rule_fire_verification을 가린 상태에서 분석가가 직접 판단하게 합니다. 이후 정답과 비교하여 역량을 평가합니다.

### 8-4. 스케일링

scaling_template의 background_composition을 참고하여 background.normal_traffic 이벤트를 추가 생성하면 200개 이벤트 규모로 확장할 수 있습니다.