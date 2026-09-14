# KR-MOB-SMISHING v1 구축활용가이드

---

## 1. 데이터셋 개요

| 항목 | 내용 |
|---|---|
| 데이터셋명 | KR-MOB-SMISHING v1 |
| 버전 | 1.0 |
| 구축일 | 2026-03-01 |
| 총 인시던트 | 100건 |
| 총 이벤트 | ~995건 |
| 형식 | JSON (인시던트당 1파일) |
| 라이선스 | CC BY-NC 4.0 |

---

## 2. 파일 구조

KR-MOB-SMISHING-100-v1/ ├── README.md # 데이터셋 소개 및 통계 ├── LICENSE # CC BY-NC 4.0 라이선스 ├── CHANGELOG.md # 버전 변경이력 ├── quality_scorecard_v1.md # 품질 지표 ├── KR-MOB-SMISHING-v1_데이터설명서.md ├── KR-MOB-SMISHING-v1_구축활용가이드.md └── incidents/ ├── inc-MOB-MAL-001.json ├── inc-MOB-BEN-002.json └── ... (100 files)


---

## 3. 빠른 시작

### 3-1. 파일 열기 (Python)

```python
import json

with open("incidents/inc-MOB-MAL-001.json", "r", encoding="utf-8") as f:
    incident = json.load(f)

print(f"ID: {incident['incident_id']}")
print(f"유형: {incident['case_type']}")
print(f"테마: {incident['theme']}")
print(f"이벤트 수: {len(incident['event_stream'])}")
3-2. 전체 파일 로드
Copyimport json, glob

incidents = []
for fp in sorted(glob.glob("incidents/*.json")):
    with open(fp, "r", encoding="utf-8") as f:
        incidents.append(json.load(f))

print(f"총 {len(incidents)}건 로드 완료")
3-3. 특정 케이스 타입만 필터링
Copymalicious = [i for i in incidents if i["case_type"] == "malicious"]
benign = [i for i in incidents if i["case_type"] == "benign"]
lookalike = [i for i in incidents if i["case_type"] == "benign_lookalike"]

print(f"malicious: {len(malicious)}, benign: {len(benign)}, lookalike: {len(lookalike)}")

## 4. 활용 시나리오

### 시나리오 1: SIEM 상관분석 규칙 개발

| 항목 | 내용 |
|---|---|
| 목적 | 5개 탐지 규칙을 SIEM에 구현하고 정확도를 측정 |

**절차:**

| 단계 | 내용 |
|---|---|
| 1 | SIEM(Elastic, Splunk 등)에 event_stream 이벤트를 인제스트 |
| 2 | 5개 상관분석 규칙을 SIEM 쿼리로 구현 |
| 3 | 각 인시던트에 대해 규칙 fire 여부 확인 |
| 4 | rule_fire_verification의 fires 값과 비교 |
| 5 | TPR(True Positive Rate), FPR(False Positive Rate) 산출 |

**예상 지표:**

| 지표 | 목표 |
|---|---|
| TPR (True Positive Rate) | >= 95% |
| FPR (False Positive Rate) | <= 5% |

### 시나리오 2: SOC 분석가 훈련

| 항목 | 내용 |
|---|---|
| 목적 | 분석가의 스미싱 탐지 역량 측정 및 훈련 |

**절차:**

| 단계 | 내용 |
|---|---|
| 1 | event_stream만 분석가에게 제공 (라벨 비공개) |
| 2 | 분석가가 각 인시던트를 malicious/benign_lookalike/benign으로 분류 |
| 3 | case_type 정답과 비교하여 정확도 측정 |
| 4 | 난이도별(DT-HIGH/MEDIUM/LOW) 정확도를 분리 분석 |
| 5 | 오답 케이스에 대해 rule_fire_verification을 공개하며 피드백 |

**난이도별 활용:**

| 난이도 | 대상 | 활용 |
|---|---|---|
| DT-LOW | 신입 분석가 | 기초 훈련 |
| DT-MEDIUM | 중급 분석가 | 역량 평가 |
| DT-HIGH | 고급 분석가 | 챌린지 |

### 시나리오 3: 탐지 엔지니어링 CI/CD

| 항목 | 내용 |
|---|---|
| 목적 | 탐지 규칙 변경 시 자동 회귀 테스트 |

**절차:**

| 단계 | 내용 |
|---|---|
| 1 | CI/CD 파이프라인에 데이터셋을 테스트 입력으로 등록 |
| 2 | 규칙 변경 시 자동으로 100건 인시던트에 대해 규칙 실행 |
| 3 | 기대 결과(rule_fire_verification)와 비교 |
| 4 | 회귀 발생 시 파이프라인 실패 처리 |

### 시나리오 4: 퍼플팀 훈련

| 항목 | 내용 |
|---|---|
| 목적 | 레드팀/블루팀 합동 훈련 시나리오 제공 |

**절차:**

| 단계 | 내용 |
|---|---|
| 1 | malicious 케이스의 event_stream을 레드팀 공격 시뮬레이션으로 활용 |
| 2 | 블루팀이 실시간으로 탐지 및 대응 |
| 3 | benign_lookalike 케이스를 오탐 훈련에 활용 |
| 4 | 훈련 후 rule_fire_verification으로 결과 리뷰 |

### 시나리오 5: 200 이벤트 스케일링

| 항목 | 내용 |
|---|---|
| 목적 | 실제 환경에 가까운 노이즈 비율로 확장 |

**절차:**

| 단계 | 내용 |
|---|---|
| 1 | 각 인시던트의 scaling_template.background_composition 확인 |
| 2 | 지정된 카테고리별 수량만큼 background.normal_traffic 이벤트 추가 생성 |
| 3 | 기존 event_stream에 시간순으로 삽입 |
| 4 | 총 이벤트 수가 약 200개가 되도록 확장 |

## 5. 주요 필드 해석 가이드

### case_type 해석

| 값 | 의미 | SIEM 대응 |
|---|---|---|
| malicious | 공격 완성, 피해 발생 | 반드시 탐지해야 함 (True Positive) |
| benign_lookalike | 공격 시도했으나 미완성 | 탐지하면 좋지만 미탐지도 허용 |
| benign | 정상 활동 | 탐지하면 오탐 (False Positive) |

### ground_truth 해석 (이벤트 레벨)

| 값 | 의미 |
|---|---|
| malicious | 공격 인프라와 직접 상호작용 |
| suspicious | 공격 인프라와 간접 상호작용 (피해 미발생) |
| benign | 정상 활동 (배경 노이즈 포함) |

### rule_fire_verification 해석

| 필드 | 의미 |
|---|---|
| fires: true | 해당 규칙이 발동해야 함 |
| fires: false | 해당 규칙이 발동하면 안 됨 |
| fire_path | 발동 경로 설명 |
| trigger | 트리거 이벤트 설명 |
| within_window | 윈도우 시간 내 발동 여부 |

## 6. 데이터 품질 검증

### 검증 항목 (19개)

| # | 검증 항목 |
|---|---|
| 1 | incident_id 형식 검증 |
| 2 | case_type 유효값 검증 |
| 3 | theme 존재 여부 |
| 4 | difficulty_tier 유효값 검증 |
| 5 | timeline_profile 존재 여부 |
| 6 | start_time / end_time RFC 3339 검증 |
| 7 | event_stream 시간순 정렬 검증 |
| 8 | event_id UUID4 형식 검증 |
| 9 | event_id 중복 검증 |
| 10 | 필수 필드 존재 검증 (entity, network, object, correlation, label) |
| 11 | log_source 카테고리명 검증 |
| 12 | ground_truth 유효값 검증 |
| 13 | case_type - ground_truth 정합성 검증 |
| 14 | rule_fire_verification 5개 규칙 존재 검증 |
| 15 | must_fire - fires 정합성 검증 |
| 16 | 도메인 .example TLD 검증 |
| 17 | IP TEST-NET 범위 검증 |
| 18 | 전화번호 마스킹 형식 검증 |
| 19 | [TRAINING] 워터마크 존재 검증 |

### 검증 결과

| 지표 | v1 결과 |
|---|---|
| 총 검증 건수 | 100 |
| PASS | 100 (100%) |
| FAIL | 0 (0%) |

## 7. 라이선스 및 이용 조건

본 데이터셋은 CC BY-NC 4.0 라이선스로 제공됩니다.

| 허용 | 제한 |
|---|---|
| 학술 연구 | 상업적 사용 |
| 교육 목적 사용 | 재판매 |
| 비상업적 2차 가공 | 라이선스 변경 |
| 출처 표기 후 공유 | |

상업적 이용을 원하시면 담당자에게 문의해 주세요.

## 8. 문의처

| 항목 | 내용 |
|---|---|
| 이메일 | [senimanyc@gmail.com] |
| 데이터셋 페이지 | https://huggingface.co/datasets/DimensionV/KR-MOB-SMISHING-v1