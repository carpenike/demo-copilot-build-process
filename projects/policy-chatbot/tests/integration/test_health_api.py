"""Integration tests for health and readiness endpoints.

Covers: Security Policy (public endpoints), /health, /ready
"""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.health import router


def _build_health_app(
    *,
    db_ok: bool = True,
    redis_ok: bool = True,
    search_ok: bool = True,
    openai_ok: bool = True,
) -> "FastAPI":  # noqa: F821
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    # Mock db_session_factory
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    if not db_ok:
        mock_ctx.__aenter__.side_effect = RuntimeError("DB down")
    app.state.db_session_factory = lambda: mock_ctx

    # Mock services
    redis = AsyncMock()
    redis.check_health = AsyncMock(return_value=redis_ok)
    app.state.redis_service = redis

    search = AsyncMock()
    search.check_health = AsyncMock(return_value=search_ok)
    app.state.search_service = search

    openai = AsyncMock()
    openai.check_health = AsyncMock(return_value=openai_ok)
    app.state.openai_service = openai

    return app


class TestHealthEndpoint:
    """IT-HEALTH-001: GET /health liveness probe."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self) -> None:
        """GET /health returns 200 with status healthy."""
        app = _build_health_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_requires_no_auth(self) -> None:
        """GET /health is public — no auth header needed."""
        app = _build_health_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200


class TestReadyEndpoint:
    """IT-HEALTH-002: GET /ready readiness probe."""

    @pytest.mark.asyncio
    async def test_ready_all_healthy(self) -> None:
        """GET /ready returns 200 when all dependencies are ok."""
        app = _build_health_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"] == "ok"
        assert data["checks"]["redis"] == "ok"
        assert data["checks"]["search"] == "ok"
        assert data["checks"]["openai"] == "ok"

    @pytest.mark.asyncio
    async def test_ready_returns_503_when_dependency_down(self) -> None:
        """GET /ready returns 503 when search is down."""
        app = _build_health_app(search_ok=False)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["search"] == "error"

    @pytest.mark.asyncio
    async def test_ready_requires_no_auth(self) -> None:
        """GET /ready is public — no auth header needed."""
        app = _build_health_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/ready")

        assert response.status_code == 200
