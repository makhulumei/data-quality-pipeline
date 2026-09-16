FROM python:3.12.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --upgrade pip==26.2.1 \
    && python -m pip install --no-cache-dir --requirement requirements.lock

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir hatchling==1.27.0 \
    && python -m pip install --no-cache-dir --no-deps --no-build-isolation . \
    && python -m pip uninstall --yes hatchling pathspec trove-classifiers \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["uvicorn", "data_quality_pipeline.api:app", "--host", "0.0.0.0", "--port", "8000"]
