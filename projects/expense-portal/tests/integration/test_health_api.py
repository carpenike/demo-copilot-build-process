"""Integration tests for health and readiness endpoints.

Covers: NFR-019
"""

import pytest
from httpx import ASGITransport, AsyncClient


def _build_health_app():
    from fastapi import FastAPI
    from app.api.health import router

    app = FastAPI()
    app.include_router(router)
    return app


class TestHealthEndpoint:
    """IT-OPS-001: /health liveness probe."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self):
        """IT-OPS-001: /health returns 200 OK with status (NFR-019)."""
        app = _build_health_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_requires_no_authentication(self):
        """Health endpoint is public — no auth required."""
        app = _build_health_app()
        # No session / auth headers — should still return 200
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
