FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY tests ./tests

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
