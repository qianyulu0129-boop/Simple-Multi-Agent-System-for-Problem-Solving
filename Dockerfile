# ---- Build stage: install dependencies into an isolated virtualenv ----
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements-web.txt .
RUN pip install -r requirements-web.txt


# ---- Runtime stage: slim image with only the app and its venv ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080 \
    OUTPUT_ROOT=/tmp/outputs

# Run as an unprivileged user
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser settings/ ./settings/
COPY --chown=appuser:appuser config/mock_config.py ./config/mock_config.py

USER appuser
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8080\")}/api/health', timeout=3)"

# Cloud Run injects $PORT; default to 8080 locally
CMD ["sh", "-c", "exec uvicorn src.medical_triage_system.web_app:app --host 0.0.0.0 --port ${PORT}"]
