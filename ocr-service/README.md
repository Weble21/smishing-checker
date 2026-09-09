# 통합 FastAPI 분석 서비스

기존 PaddleOCR `/ocr` API에 KoELECTRA 문자 분류, URL 구조·VirusTotal 평판 분석, 이미지 통합 `/analyze` API를 추가했습니다. 자세한 설치, 환경변수와 실행 방법은 프로젝트 루트의 `README.md`를 참고하세요.

주요 함수는 다음 모듈에 분리되어 있습니다.

- `smishing_api/ocr.py`: PaddleOCR 지연 로딩과 문자 추출
- `smishing_api/text_model.py`: 저장된 이진 KoELECTRA 지연 로딩과 CUDA/CPU 추론
- `smishing_api/url_analysis.py`: URL 추출·정규화·구조 검사·VirusTotal 조회
- `smishing_api/risk.py`: 문자 결과와 URL 결과 종합

서비스는 업로드 파일을 디스크에 저장하지 않으며, 대상 URL에 접속하지 않고 VirusTotal의 기존 보고서만 조회합니다.
