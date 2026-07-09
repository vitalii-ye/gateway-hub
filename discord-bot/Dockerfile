FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /app

COPY discord-bot/pyproject.toml ./
RUN uv sync --no-dev

COPY discord-bot/ ./

ENV PYTHONPATH=/app
EXPOSE 8001

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
