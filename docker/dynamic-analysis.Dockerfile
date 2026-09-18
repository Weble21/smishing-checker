FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/pwuser

WORKDIR /app
COPY dynamic-analysis-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY dynamic-analysis-service /app
RUN python -m compileall -q /app && chown -R pwuser:pwuser /app

USER pwuser
EXPOSE 8081
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "1", "--limit-concurrency", "32"]
