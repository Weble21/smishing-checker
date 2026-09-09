# 안심문자 — 스미싱 위험 분석 웹서비스

휴대폰 문자·카카오톡 스크린샷을 올리면 OCR, KoELECTRA 이진 문자 분류, URL 구조 검사와 VirusTotal 기존 보고서를 종합해 `HIGH`, `MEDIUM`, `LOW` 위험도를 안내합니다. `LOW`는 안전 보증이 아니라 현재 분석에서 뚜렷한 위험 요소가 발견되지 않았다는 의미입니다.

## 처리 흐름

```text
모바일 웹
  → POST /api/v1/messages/analyze (Spring Boot)
  → POST /analyze (FastAPI)
  → PaddleOCR
  → 저장된 KoELECTRA NORMAL/RISK 분류
  → URL 구조 검사 + VirusTotal 기존 보고서 조회
  → 명시적 규칙으로 위험도 종합
  → 기존 AnalysisResponse로 변환 후 결과 화면 표시
```

업로드 이미지는 두 서비스 모두 메모리에서만 처리하며 파일이나 OCR 원문을 로그에 기록하지 않습니다. FastAPI는 대상 URL에 직접 접속하거나 VirusTotal에 새 URL을 제출하지 않습니다.

## 환경변수

`.env.example`을 참고해 프로젝트 루트에 `.env`를 만들 수 있습니다. 실제 키는 커밋하지 마세요.

| 이름 | 기본값 | 설명 |
|---|---|---|
| `AI_BASE_URL` | `http://127.0.0.1:8000` | Spring이 호출할 FastAPI 주소 |
| `AI_CONNECT_TIMEOUT` | `3s` | FastAPI 연결 제한 시간 |
| `AI_READ_TIMEOUT` | `60s` | FastAPI 분석 응답 제한 시간 |
| `SMISHING_PROJECT_DIR` | 저장소 루트 자동 탐색 | 모델 탐색 기준 경로 |
| `SMISHING_MODEL_DIR` | 최신 `experiments/koelectra-*/model` | 저장된 이진 분류 모델 경로 |
| `VT_API_KEY` | 없음 | VirusTotal API 키 |
| `VT_TIMEOUT_SECONDS` | `5` | VirusTotal 조회 제한 시간 |
| `TEXT_HIGH_THRESHOLD` | `0.80` | 문자 고위험 점수 기준 |
| `TEXT_MEDIUM_THRESHOLD` | `0.60` | 문자 주의 점수 기준 |
| `URL_SUSPICIOUS_THRESHOLD` | `0.40` | URL 구조 의심 점수 기준 |
| `OCR_DEVICE` | `cpu` | PaddleOCR 장치 (`cpu` 또는 환경에 맞는 GPU 값) |
| `OCR_MIN_CONFIDENCE` | `0.55` | 통합 분석을 진행할 최소 OCR 신뢰도 |
| `OCR_CACHE_DIR` | `.cache/ocr` | PaddleOCR 모델 캐시 경로 |

`HF_TOKEN`, `OCR_API_URL`은 원격 저장소의 이전 개별 분석 클라이언트 호환 설정이며 현재 기본 통합 흐름에서는 사용하지 않습니다.

## FastAPI 설치와 실행

Python 3.10~3.12 가상환경을 권장합니다. CUDA용 PyTorch와 PaddlePaddle은 로컬 CUDA 환경에 맞는 공식 빌드를 먼저 설치한 뒤 나머지 요구사항을 설치하세요. CPU에서도 추론할 수 있습니다.

```powershell
python -m venv ocr-service/.venv
ocr-service/.venv/Scripts/python.exe -m pip install --upgrade pip
ocr-service/.venv/Scripts/python.exe -m pip install -r ocr-service/requirements.txt
ocr-service/.venv/Scripts/python.exe -m uvicorn app:app `
  --app-dir ocr-service `
  --host 127.0.0.1 `
  --port 8000
```

확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/url/analyze `
  -ContentType application/json `
  -Body '{"text":"택배 주소 확인 http://example.com"}'
```

## Spring Boot 실행

Java 21이 필요합니다.

```powershell
.\gradlew.bat bootRun
```

브라우저에서 `http://localhost:8080`에 접속합니다.

## 테스트

VirusTotal은 테스트에서 `httpx.MockTransport`로 대체되며 실제 외부 API를 호출하지 않습니다.

```powershell
.\gradlew.bat test
ocr-service/.venv/Scripts/python.exe -m pytest ocr-service/tests
```

## Docker로 실행

Docker Desktop의 Linux 컨테이너 엔진을 켠 뒤 프로젝트 루트에서 실행합니다.
로컬 모델 파일이 필요합니다: `experiments/canine-url-v1/model`,
`experiments/canine-url-v1/internal_test_metrics.json`,
`experiments/koelectra-baseline-v2-20260907T015430973273Z/checkpoints/checkpoint-497`.
문자 모델 위치가 다르면 `DOCKER_TEXT_MODEL_DIR`로 지정하세요.

```powershell
docker compose up -d --build
docker compose ps
docker compose logs --tail 100 fastapi
```

Windows에서 빌드가 시작 단계에서 멈추거나 학습 데이터 폴더 탐색이 오래 걸리면,
필요한 소스만 모으는 스크립트로 실행합니다. 이 PC에서 확인한 우회 방법입니다.

```powershell
powershell -ExecutionPolicy Bypass -File docker/up.ps1 -LegacyBuilder
```

BuildKit이 정상인 환경에서는 `-LegacyBuilder`를 생략합니다.
스크립트의 작은 빌드 컨텍스트는 `.cache/docker-build-*`에 남으며 Git에 포함되지 않습니다.

웹: `http://localhost:18080`, API 문서: `http://localhost:18000/docs`.
기존 8080·8000 서버와 별도로 실행합니다. `DOCKER_WEB_PORT`, `DOCKER_API_PORT`로 변경할 수 있습니다.
Spring은 컨테이너 내부의 `http://fastapi:8000`에 연결합니다.
문자·URL·OCR 모델을 시작 시 로딩하며 모두 준비되어야 웹이 시작됩니다.
첫 실행은 패키지·이미지·OCR 모델 다운로드로 시간이 걸립니다. OCR 모델은 이름 있는 볼륨에 유지됩니다.
모델 파일은 읽기 전용 바인드 마운트이므로 다른 서버로 옮길 때 함께 배치해야 합니다.
CSV와 코드는 이미지에 포함되므로 변경 후 `docker compose up -d --build`로 반영합니다.
현재 구성은 CPU 1개 작업 프로세스로 실행하며 HTTPS가 없는 로컬 시험 실행용입니다.

로컬 Docker 검증: Spring 테스트·JAR 빌드 성공, 문자·URL·OCR 모델 로딩 성공,
웹 GET 및 Spring 경유 multipart 분석 성공. CJ대한통운 원본 배송 이미지는
약 9.4초에 `SUCCESS` / `LOW`를 반환했습니다. 이 시간은 해당 PC의 단일 요청 측정값입니다.
브라우저 화면 조작과 휴대폰 접속은 별도 확인이 필요합니다.

```powershell
# 로그 보기
docker compose logs -f --tail 100
# 종료 (모델 원본과 OCR 볼륨은 유지)
docker compose down
```

## AWS CI/CD

기존 EC2/ECR 배포에 자동 테스트와 검증 배포를 적용하는 방법은
[배포 가이드](docs/deployment.md)를 참고하세요. main 대상 PR에서는 테스트만,
main push에서는 테스트 성공 후 이미지 빌드·배포·헬스체크까지 실행합니다.

## API 목록

- `POST /api/v1/messages/analyze`: 브라우저용 Spring multipart API (`image`)
- `POST /analyze`: 이미지 한 장을 받는 통합 FastAPI (`image`)
- `POST /url/analyze`: 텍스트의 URL만 분석하는 FastAPI
- `POST /ocr`: 기존 개별 OCR 호환 API
- `GET /health`: OCR·문자·URL 모델 로딩 상태

## URL Transformer 모델

URL 모델은 `experiments/canine-url-v1/model`의 CANINE Transformer를 사용합니다.
`URL_MODEL_PATH`는 기존 joblib 파일 대신 Transformer 모델 **폴더**를 지정합니다.
해당 폴더의 상위 경로에 학습 결과 `internal_test_metrics.json`도 함께 두어야 합니다.
여기에 저장된 `threshold`를 사용하며 URL 전처리와 최대 길이 256은 학습 노트북과 같습니다.
모델 파일은 로컬에서만 읽고 CUDA가 없으면 CPU로 실행합니다.

`GET /health`의 `urlModel.loaded`, `modelPath`, `threshold`, `error`로 로딩을 확인하세요.
`POST /url/analyze`의 결과에 숫자 `modelScore`가 나오면 URL 모델 추론까지 수행된 것입니다.
로드 실패 시 `modelScore`는 `null`이며 구조·평판 분석만 계속됩니다.
URL 판정이 하나라도 `SUSPICIOUS` 또는 `DANGEROUS`이면 최종 `HIGH`입니다.
`MEDIUM`은 URL이 없고 개인정보·신용정보·인증정보 요구 또는 송금 유도가 있을 때만 적용합니다.
그 외는 `LOW`이며, 평판 미확인·미등록 도메인·문자 모델 점수만으로 등급을 올리지 않습니다.
URL이 있지만 위험 판정이 없으면 문자 요구와 무관하게 `LOW`입니다. 이는 안전 보증이 아닙니다.

## CSV 화이트리스트

`dataset/whiteList/official_domains.csv`를 공식·메신저 도메인 판별에 사용합니다.
`OFFICIAL_DOMAINS_PATH`로 파일 경로를 변경할 수 있습니다. 목록은 메모리에 캐시되므로
CSV 수정 후 FastAPI를 재시작하세요. 파일을 읽을 수 없으면 공식 도메인으로 인정하지 않습니다.
기존 `config/official_domain_seeds.json`은 CSV에 등록된 같은 브랜드·도메인의 별칭 보완에만 사용합니다.

실제 호스트의 정확한 도메인 또는 점으로 구분된 하위 도메인을 매칭하며,
가장 구체적인 등록 도메인을 우선합니다. 따라서 `open.kakao.com`은 `kakao.com`보다
우선하여 메신저로 처리합니다. 같은 도메인의 여러 브랜드(NAVER·네이버쇼핑)는 함께 인식합니다.
공식 도메인은 URL 모델 점수가 높아도 모델에 의한 의심 판정을 취소합니다.
원래 `modelScore`는 확인용으로 유지하지만 최종 URL `riskScore`에 반영하지 않습니다.
VirusTotal 의심·악성 탐지와 URL 구조 위험은 유지합니다.
문자 모델 점수는 참고 정보로만 표시하며 최종 등급을 올리지 않습니다.
OCR로 줄바꿈된 URL의 경로·쿼리는 이어 붙여 `trust.do` 같은 경로가 별도 도메인으로
잘못 추출되는 것을 줄입니다. 다음 줄의 독립 URL은 별도로 분석합니다.
메신저로 등록된 주소에는 이 예외를 적용하지 않습니다.

`dataset/whiteList/message_url_pairs_450.csv`는 정상·주의·위험 사례를 포함하므로
운영 허용 목록 대신 `ocr-service/tests/test_whitelist.py`의 450건 회귀 테스트에 사용합니다.
문자와 URL만 판별 함수에 전달하고 라벨·주석을 모델 판단으로 사용하지 않습니다.
이 테스트는 OCR·모델·VirusTotal을 실행하지 않고 종합 판별 규칙만 검증합니다.
450건에는 URL 판정을 `UNKNOWN`으로 주입하여 미확인 URL만으로 등급을 올리지 않는지
검증합니다. 위험 URL과 URL 없는 민감정보·송금 요구는 별도 정책 테스트로 검증합니다.
따라서 테스트 통과는 데이터 라벨 정확도 100%를 뜻하지 않습니다.

## 모델의 현재 한계

저장된 모델은 `NORMAL`과 `RISK`를 구분하는 이진 KoELECTRA 모델입니다. 광고 문자를 별도 분리하는 3종 모델이 아닙니다. 기존 테스트셋의 정상 251건과 위험 744건에서 정확도 1.0이 기록됐지만, 데이터 생성 형식이나 클래스 고유 특징을 학습했을 가능성이 있어 실제 성능 100%를 뜻하지 않습니다. 운영 전에는 저장소의 `datat.zip` 같은 학습 외부 수동 검수 데이터로 별도 평가해야 합니다.
