# 로컬 PaddleOCR 서비스

휴대폰에서 업로드한 이미지는 Spring Boot가 이 로컬 서비스에 메모리로 전달합니다. OCR 서비스는 파일을 디스크에 저장하지 않습니다.

## 설치

프로젝트 루트에서 Python 3.10~3.12 환경으로 실행합니다.

```powershell
python -m venv ocr-service/.venv
ocr-service/.venv/Scripts/python.exe -m pip install --upgrade pip
ocr-service/.venv/Scripts/python.exe -m pip install -r ocr-service/requirements.txt
```

## 실행

```powershell
ocr-service/.venv/Scripts/python.exe -m uvicorn app:app `
  --app-dir ocr-service `
  --host 127.0.0.1 `
  --port 8001
```

첫 OCR 요청에서는 한국어 PP-OCRv5 모델을 내려받기 때문에 시간이 더 걸릴 수 있습니다. 기본값은 CPU이며 GPU를 사용하려면 PaddlePaddle 설치와 `OCR_DEVICE` 값을 환경에 맞게 별도로 설정해야 합니다.

정상 실행 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

이미지 OCR 확인:

```powershell
curl.exe -F "image=@evaluation/images/case-01-delivery-address.png;type=image/png" `
  http://127.0.0.1:8001/ocr
```
