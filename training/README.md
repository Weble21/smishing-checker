# 간접 유도 추가 학습

기존 KoELECTRA 체크포인트를 이어 학습합니다. URL 모델과 운영 모델 경로는 변경하지 않습니다.
`indirect_lures.csv`는 위험 12개/정상 12개의 **합성 초기 사례**이며 실제 신고 데이터가 아닙니다.
인증 미완료에 따른 불이익, 반송 압박, 혜택 상실, 보안 프로그램 설치 유도와
정상 인증/점검/배송 안내를 함께 제공합니다. URL은 예시용 `.example` 주소이며,
정상·위험 양쪽에 넣었습니다. 도메인 자체가 악성이라는 학습 라벨이 아닙니다.

이 추가 데이터의 라벨 기준은 다음과 같습니다.

- NORMAL(0): 문자 속 링크를 이용하지 않고 기존에 설치한 앱을 직접 열어 확인하도록 안내합니다.
  인증 미완료, 지급 보류, 서비스 정지 등의 표현이 있어도 이 안내만으로 위험 라벨을 붙이지 않습니다.
- RISK(1): 문자에 제시한 링크에서 인증·민감정보 입력·결제·프로그램 설치 등을 하도록 유도합니다.
  직접적인 클릭 명령뿐 아니라 미처리 시 불이익을 내세운 간접 유도도 포함합니다.
- 단순 공지에 URL이 포함된 것과 링크를 통한 행동 유도는 구별합니다.
  이 합성 데이터의 분류 기준이며, 모든 실제 링크가 악성이라는 의미는 아닙니다.

같은 불이익 안내에서 링크 처리와 기존 앱 직접 실행만 다르게 구성한 정상·위험 쌍을
포함해, 모델이 '인증'이나 '정지'라는 단어만 외우지 않도록 했습니다.

학습 16개, 검증 4개, 테스트 4개이며 같은 시나리오 계열은 분할을 넘지 않습니다.
작은 합성 테스트의 성적을 실제 탐지율로 해석하면 안 됩니다. 사용자 제공 PI MINE 문자는
이번 문제를 발견한 개발 사례이므로 독립 테스트 점수로 보고하지 않습니다.

원래 체크포인트 학습에 사용한 `train.csv`, `valid.csv`, `test.csv`를 준비하세요.
필수 컬럼은 `text,label`이고 라벨은 NORMAL=0, RISK=1입니다. 기존 데이터를 다시
무작위 분할하면 학습에서 본 문자가 테스트에 섞일 수 있으므로 원래 분할을 유지합니다.
신규 사례만 반복 학습하지 않고 기존 학습 데이터를 모두 섞어 기존 성능 손실을 점검합니다.

```powershell
ocr-service/.venv/Scripts/python.exe training/finetune_indirect.py --base-splits <기존-실험/splits> --output experiments/indirect-prepare --prepare-only
ocr-service/.venv/Scripts/python.exe training/finetune_indirect.py --base-splits <기존-실험/splits> --model-dir <기존-KoELECTRA-model> --output experiments/indirect-run-001
```

학습 의존성은 기존 노트북의 torch, transformers, datasets, accelerate, numpy입니다.
체크포인트는 로컬에서만 읽으며 새 모델 다운로드/API 호출은 하지 않습니다.
`comparison.json`에는 학습 전후 기존 테스트와 간접 유도 테스트의 위험 재현율,
정밀도, 정상 오탐률을 각각 저장합니다. `candidate`는 검토용이며 자동 배포하지 않습니다.
개선과 오탐률을 확인한 뒤 별도의 실제 문자 평가를 거쳐 운영 경로를 변경하세요.

현재 `risk.py`는 문자 모델 점수만으로 등급을 올리지 않습니다. 공동 입력 모델은 미확인 URL과 행동 요구 문맥이 함께 있을 때 간접 유도 판정을 보완합니다. 모델 재학습과
최종 판정 규칙 검증은 별개이며, 이미지 → OCR → URL → 최종 등급도 함께 확인해야 합니다.

## 이전 가중치가 없는 경우

`retrain_from_notebook.py --output experiments/indirect-new-run`은 노트북의
`monologg/koelectra-base-v3-discriminator`와 `meal-bbang/Korean_message`를 받아
새 이진 분류기를 학습합니다. 모델과 데이터 revision을 기록하고 원본 라벨 2→RISK,
3→NORMAL을 유지합니다. 기존 운영 모델의 가중치를 이어 학습하는 것은 아닙니다.
이 경우 `comparison.json`의 before는 학습 전 초기 분류기이며 운영 모델 성능이 아닙니다.

2026-09-11 실행에서는 모델·데이터 준비 후 CUDA 오류가 발생했고 NVIDIA 진단은
`GPU is lost. Reboot the system to recover this GPU`를 반환했습니다. 학습은 완료되지 않았습니다.
GPU 복구 후 준비된 파일을 사용해 실행할 수 있습니다(출력 폴더는 존재하지 않는 경로 지정).

```powershell
& 'C:/Users/SSAFY/AppData/Local/Programs/Python/Python312/python.exe' training/finetune_indirect.py --base-splits experiments/indirect-notebook-20260911/base_splits --model-dir experiments/indirect-notebook-20260911/initial --output experiments/indirect-notebook-20260911/trained-retry --epochs 3
```

GPU를 사용하지 않으려면 `--cpu`를 추가할 수 있지만 학습 시간이 길어질 수 있습니다.

## 문자와 링크 관계를 함께 학습

`brand_link_pairs.csv`에 동일한 안내문에 공식 목록에 등록된 도메인과 사칭 도메인을
각각 붙인 합성 12건을 추가했습니다. 국민은행은 학습, 신한은행은 검증, 우리은행은
테스트로 구분했습니다. 총 신규 사례는 간접 유도 24건 + 기관/링크 쌍 12건입니다.
공식 링크 사례의 정상 라벨은 이 합성 안내 상황에 대한 것이며, 공식 도메인만으로
모든 문자가 안전하다는 보장은 아닙니다. 다른 기관 도메인과 목록 미확인도 구별합니다.

학습 및 서비스는 `message_context.py`의 같은 전처리를 사용합니다. 모델 입력에는
문자 본문뿐 아니라 URL에서 추출한 실제 호스트와 언급 기관의 공식 도메인 관계를
포함합니다. URL 경로나 쿼리에 들어 있는 기관명은 본문의 기관 주장으로 취급하지 않습니다.
`kbstar.com.evil.example`과 `kbstar.com@evil.example`은 국민은행 도메인으로 인정하지 않습니다.
라벨 및 CSV의 정답 주석은 입력 특징으로 사용하지 않습니다.

관계 정보는 최대 96토큰, 전체는 256토큰으로 제한합니다. 긴 문자는 일부 잘리고,
링크가 매우 많으면 개별 호스트도 일부 잘릴 수 있지만 관계 종류 요약은 앞에 둡니다.
공식 도메인 출처는 `official_domains.csv` 및 별칭 seed이며 해시를 학습 manifest에 기록합니다.
목록 누락은 악성 확정이 아니고, 도메인 등록 여부가 SMS 발신자를 인증하지도 않습니다.

새 모델 config에 `smishing_input_schema=message-domain-v1`이 저장돼 같은 전처리를
서비스에서도 선택합니다. 이 값이 없는 기존 모델은 이전 입력 방식을 유지합니다.
`comparison.json`의 `brand_link`에서 기관/링크 쌍 테스트를 별도로 확인합니다.


## 노트북에서 새 문자 모델 학습

프로젝트 루트의 `smishing-checker.ipynb`를 Python 3.12 커널로 순서대로 실행합니다.
원본 정제·그룹 분리 → 검토된 KR-MOB 및 간접 유도/기관 링크 쌍 병합 →
공통 문자·도메인 인코딩 → KoELECTRA 튜닝 → 독립 테스트 오탐률 평가 → 후보 저장으로 구성됩니다.
출력은 `experiments/message-context-<실행시각>/candidate`이며 자동 배포하지 않습니다.
노트북은 현재 프로젝트 루트를 사용하며 Colab 전용 마운트는 호출하지 않습니다.
GPU 오류가 있으면 학습 전 중단합니다. CPU 학습은 노트북의 `USE_CPU=True`로 명시합니다.

모델은 NORMAL/RISK 이진 분류이며, 최종 3단계 정책은 `risk.py`에서 적용합니다.
개인정보·인증정보 요구 또는 송금 요청은 URL 없음/공식 URL이어도 최소 MEDIUM입니다.
이미 HIGH인 URL 판정은 유지합니다. 예방 안내와 입금 완료·결제 내역 조회는 요청과 구분합니다.
이 요청 구분은 현재 규칙 기반으로, 모든 표현에 대한 문맥 이해가 보장되는 것은 아닙니다.


## 수정 후 파이프라인 검증

```powershell
py -3.12 -m pytest ocr-service/tests training/test_finetune_indirect.py training/test_filter_kr_mob.py -q
py -3.12 training/validate_notebook_pipeline.py
```

두 번째 명령은 다운로드 없이 임시 소형 무작위 Electra 모델과 합성 원본을 사용해
노트북의 정제·그룹 분리·실제 보조 CSV 병합·토큰화·1-step 학습·평가·저장·서빙 재로딩을 검증합니다.
학습 입력과 서빙 입력의 토큰 일치 및 `[batch, sequence]` 텐서 차원도 확인합니다.
이 결과는 실제 모델 정확도나 전체 데이터 학습 완료를 의미하지 않습니다.

문맥 보조 판정은 `message-domain-v1` 공동 입력 모델에만 허용합니다.
기존 본문 전용 모델에는 적용하지 않으며 미확인 URL + 행동 요구 문맥 + RISK 점수 0.9 이상일 때만
간접 유도 판정을 보완합니다. 0.9는 정책 임계값으로, 실데이터에서 보정된 확률은 아닙니다.
URL 없음/공식 URL은 점수만으로 등급을 올리지 않고 개인정보·송금 요구를 별도 검사합니다.
이름·생년월일 요구, 띄어 쓴 이체 요청, 예방 안내 뒤의 별도 송금 요청을 구분하고
개인정보 입력 완료 알림은 요구로 처리하지 않습니다. 규칙 기반 처리의 표현 범위에는 한계가 있습니다.


## 데이터·평가 프로토콜 개선

`smishing-checker.ipynb`는 원본 일반 대화 class 1을 정상에 포함합니다.
URL/숫자/고객 이름 정규화 후 문자 3-gram Jaccard >= 0.9인 문장들의 연결 성분을 **분할 전에** 묶습니다.
연결 성분의 양 끝 문장은 서로 0.9 미만일 수도 있으며, 그룹이 너무 커지면 데이터를 검토해야 합니다.
보조 데이터 및 외부 평가 데이터가 다른 split과 유사 그룹을 공유하면 중단합니다.

`RUN_ABLATIONS=True`이면 고정 분할과 동일 초기 모델에서 none/url/digit/prefix/shuffle을 각각 1에폭 학습합니다.
URL 제거 시 도메인 관계 입력도 다시 계산합니다. 각 모드는 valid만 평가하고 test를 튜닝에 사용하지 않습니다.
결과는 `ablations/ablation_results.json`에 저장됩니다. 점수 유지나 하락 하나만으로 라벨 누수를 확정하지 마세요.
기본값 False는 5회 학습 비용을 자동 발생시키지 않기 위한 것이며 실행하지 않은 점수는 기록하지 않습니다.

최대 5에폭, 200스텝 이내 간격 평가·저장, early stopping patience 3을 사용합니다.
체크포인트는 macro F1으로 고르며 ROC-AUC/AP도 함께 기록합니다. risk recall만 최대화하지 않습니다.
`threshold.json`은 valid에서 정상 오탐률 1% 이하 조건을 만족하는 위험 재현율 최대 임계값을 기록합니다.
동점은 더 낮은 오탐률과 더 높은 임계값을 선호합니다. 모든 예측이 같은 극단값이어도 안전하게 전체 정상 선택을 표현할 수 있습니다.
이는 유한 검증 표본의 경험적 오탐률이지 서비스 오탐률 보장이 아닙니다.
선택값은 모델 config에 저장되어 서빙에도 적용됩니다. 기존 모델에는 기본 0.5를 유지합니다.

외부 데이터 형식은 `evaluation_sets/README.md`를 참고하세요. 현재 외부 실제 데이터는 없으므로 미평가입니다.
`validate_notebook_pipeline.py`는 소형 임시 모델로 다섯 제거 모드까지 실행해 연결만 검증합니다.
그 결과는 실제 모델의 ablation 성능이 아닙니다.


## 공개 자료 보완 실험 (message-context-v4-public)

`evaluation_sets/public_sources.json`에 기록한 공식·서비스 제공자 자료를 바탕으로 재작성한 정상 예시를 추가했습니다.
실제 수신 문자와 구분하며 train 23 / valid-hard 16 / test-hard 12건입니다. 서로 다른 출처 계열을 사용합니다.
정상 23건은 학습 텐서에서만 8회 노출하여 보조 데이터의 영향을 확보하며 독립 관측 수로 부풀리지 않습니다.
체크포인트 점수는 `macro_f1 - hard_normal_false_positive_rate`입니다.
최종 임계값은 일반 valid의 오탐률 1% 이하, valid-hard 각 유형의 오탐률 1% 이하, 위험 재현율 95% 이상을 동시에 만족해야 합니다.
조건 불충족이면 `no_feasible_threshold`로 기록하고 테스트를 보며 임계값을 고치지 않습니다.
새 출처 기반 예시는 파일 origin/review_method에 표시했습니다. 실제 temporal 평가 세트는 여전히 없습니다.

`py -3.12 -u training/execute_training_notebook.py`로 디스크 노트북의 스냅샷을 실행할 수 있습니다.
각 실험 폴더의 `executed.ipynb`와 `notebook_source.sha256`에 실행 셀 및 원본 해시가 남습니다.
공개 재작성 예시만으로 실제 서비스 오탐률이나 발신자 진위를 보장할 수 없습니다.

### 금융 정상 문자 합성 데이터

`generate_financial_normal_synthetic.py`는 카드사 공식 이용알림 설명과 Kakao 카드 SMS 파서 픽스처만으로 `financial_normal_synthetic.csv`를 재현 가능하게 생성합니다. 데이콘 거래 데이터의 V1~V30에는 문자 의미가 없으므로 train/val/test 모두 읽거나 사용하지 않습니다. 합성 데이터는 train에 한 번만 추가되고 독립 평가에는 사용하지 않습니다.

```powershell
py -3.12 training/generate_financial_normal_synthetic.py --count 300
```

