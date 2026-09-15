> 2026-09-15 변경: 최종 판정은 [URL 우선 정책](../docs/url-first-policy.md)을 따릅니다. /analyze의 LLM 보조 판정 호출은 제거됐으며 아래 LLM 연결 설명은 이전 구현 기록입니다.

# 통합 FastAPI 분석 서비스

기존 PaddleOCR `/ocr` API에 KoELECTRA 문자 분류, URL 구조·VirusTotal 평판 분석, 이미지 통합 `/analyze` API를 추가했습니다. 자세한 설치, 환경변수와 실행 방법은 프로젝트 루트의 `README.md`를 참고하세요.

주요 함수는 다음 모듈에 분리되어 있습니다.

- `smishing_api/ocr.py`: PaddleOCR 지연 로딩과 문자 추출
- `smishing_api/text_model.py`: 저장된 이진 KoELECTRA 지연 로딩과 CUDA/CPU 추론
- `smishing_api/url_analysis.py`: URL 추출·정규화·구조 검사·VirusTotal 조회
- `smishing_api/risk.py`: 문자 결과와 URL 결과 종합

서비스는 업로드 파일을 디스크에 저장하지 않으며, 대상 URL에 접속하지 않고 VirusTotal의 기존 보고서만 조회합니다.

## 문맥 판단 프롬프트

`smishing_api/prompts/smishing_review.txt`에 발신자 주장, 인증·송금·설치 요구,
불이익 위협, 공식 도메인과의 관계를 함께 판단하는 지침을 저장했습니다.
KoELECTRA는 이진 분류기이므로 이 프롬프트를 직접 이해하거나 학습하지 않습니다.
`/analyze`는 기존 분석 이후 선택적으로 지시형 LLM을 호출해 최종 등급에 반영합니다.
LLM 미연결 상태에서도 신원확인 + 서비스 중단 위협 + 공식 연관성 미확인 링크는
MEDIUM 이상이며, URL도 의심이면 HIGH입니다. 미확인 결과를 정상이라고 표현하지 않습니다.

Ollama에서 사용할 지시형 모델을 준비한 뒤 다음 환경변수를 설정하고 API를 재시작합니다.

```dotenv
CONTEXT_LLM_MODEL=설치한-모델명
CONTEXT_LLM_BASE_URL=http://127.0.0.1:11434
CONTEXT_LLM_TIMEOUT_SECONDS=30
```

Docker에서는 호스트 서버 주소로 `http://host.docker.internal:11434`를 사용합니다.
호스트의 Ollama가 컨테이너에서 접근 가능한 인터페이스로 수신해야 합니다.
운영에서는 실제 접근 가능한 내부 서버 주소를 지정하세요. API 요청 전체 제한 시간은
OCR·분류·URL 조회·LLM 시간을 합친 것보다 길게 설정해야 합니다.
빈 모델명은 비활성화이며 모델을 자동 설치하거나 다운로드하지 않습니다.
활성화하면 OCR 문자와 URL 분석 결과를 지정한 서버에 전송합니다.

[Ollama 구조화 출력](https://docs.ollama.com/capabilities/structured-outputs)을 사용하고
JSON 응답을 검증합니다. 기존 경고 등급은 LLM이 낮출 수 없습니다.
설정된 LLM의 시간 초과나 잘못된 응답은 기존 경고를 유지하고,
기존 LOW 결과는 문맥 분석 미완료를 명시한 MEDIUM으로 반환합니다.
프롬프트는 런타임 웹 검색을 수행하지 않으며 공식 주소나 사이트 동작을 추측하지 않도록 지시합니다.
실제 모델별 탐지율은 별도의 평가가 필요합니다.
