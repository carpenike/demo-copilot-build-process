"""Integration tests for health endpoints.

IT-016: GET /health returns 200
IT-017: GET /ready returns dependency status
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """GET /health — liveness check."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """IT-016: Health endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_requires_no_auth(self, unauthed_client: TestClient) -> None:
        """Health endpoint is accessible without authentication."""
        response = unauthed_client.get("/health")

        assert response.status_code == 200


class TestReadyEndpoint:
    """GET /ready — readiness check."""

    def test_ready_all_ok(
        self,
        client: TestClient,
        mock_db: AsyncMock,
        mock_redis: AsyncMock,
        mock_llm_service: AsyncMock,
        mock_search_service: AsyncMock,
    ) -> None:
        """IT-017: Ready endpoint returns status of all dependencies."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data

    def test_ready_requires_no_auth(self, unauthed_client: TestClient) -> None:
        """Readiness endpoint is accessible without authentication."""
        response = unauthed_client.get("/ready")

        # May return 200 or 503 depending on mock state, but not 401
        assert response.status_code in (200, 503)
