"""Integration tests for health and readiness endpoints.

Tests derived from wireframe-spec.md and enterprise security policy.
"""

from fastapi.testclient import TestClient

from app.main import create_app


class TestHealthEndpoint:
    """GET /health — liveness probe, no auth required."""

    def test_health_returns_200(self) -> None:
        """IT-HEALTH-001: Health endpoint returns 200 with status healthy."""
        app = create_app()
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_no_auth_required(self) -> None:
        """Health endpoint does not require authentication."""
        app = create_app()
        client = TestClient(app)
        # No Authorization header
        response = client.get("/health")
        assert response.status_code == 200
