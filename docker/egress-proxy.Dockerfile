FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY dynamic-analysis-service/egress_proxy.py /app/egress_proxy.py
RUN python -m compileall -q /app && useradd --system --uid 10001 --no-create-home proxyuser
USER proxyuser
EXPOSE 3128
CMD ["python", "/app/egress_proxy.py"]

