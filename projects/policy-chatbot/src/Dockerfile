# ----- Stage 1: build -----
FROM python:3.11-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /build
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project || uv pip install --system -r <(uv pip compile pyproject.toml)

COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# ----- Stage 2: runtime -----
FROM python:3.11-slim AS runtime

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

COPY --from=builder /build /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

EXPOSE 8000

USER appuser:appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
