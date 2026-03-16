# Multi-stage build for Policy Chatbot (ADR-0008)
# IMPORTANT: In production, replace python:3.11-slim with the approved internal
# registry image (e.g., acmeacr.azurecr.io/base-images/python:3.11-slim).
# The CI pipeline builds with ACR-sourced base images via --build-arg.

# Stage 1: build
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE} AS builder

WORKDIR /build

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency manifest first for layer caching
COPY pyproject.toml .

# Install dependencies
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy application code
COPY app/ app/

# Stage 2: runtime
FROM ${BASE_IMAGE} AS runtime

# Non-root user required by enterprise security policy
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /build/app app/

# Switch to non-root user
USER appuser:appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
