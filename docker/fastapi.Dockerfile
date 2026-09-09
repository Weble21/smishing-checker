FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
COPY ocr-service/requirements.txt /app/requirements.txt
RUN pip install 'torch>=2.7,<3' --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements.txt
COPY ocr-service/app.py /app/ocr-service/app.py
COPY ocr-service/smishing_api /app/ocr-service/smishing_api
COPY config/official_domain_seeds.json /app/config/official_domain_seeds.json
COPY dataset/whiteList/official_domains.csv /app/dataset/whiteList/official_domains.csv
COPY docker/start-api.py /app/start-api.py
RUN python -m compileall -q /app/ocr-service /app/start-api.py
EXPOSE 8000
CMD ["python", "/app/start-api.py"]
