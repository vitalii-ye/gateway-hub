FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

COPY gateway/pyproject.toml gateway/uv.lock* ./
RUN uv sync --frozen --no-dev

COPY gateway/ ./
COPY shared/ /app/shared

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

ENV PYTHONPATH=/app
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
