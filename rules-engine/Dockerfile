FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

COPY rules-engine/pyproject.toml ./
RUN uv sync --no-dev

COPY rules-engine/ ./
COPY shared/ /app/shared

ENV PYTHONPATH=/app
CMD ["uv", "run", "python", "main.py"]
