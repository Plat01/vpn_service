FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .

RUN uv sync --no-dev --no-editable

FROM python:3.12-slim AS runtime

WORKDIR /app

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

COPY --from=builder /app/.venv /app/.venv

COPY src/ ./src/
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY pyproject.toml ./
COPY entrypoint.sh ./entrypoint.sh

RUN chmod +x /app/entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

USER appuser

EXPOSE 8000

CMD ["./entrypoint.sh"]