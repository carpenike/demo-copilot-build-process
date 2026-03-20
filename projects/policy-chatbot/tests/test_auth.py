"""Unit tests for the authentication module (app/core/auth.py).

Covers: Auth boundary tests (401, 403), CurrentUser model
User Stories: US-001 (auth required), US-008 (admin role required)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.core.auth import CurrentUser, get_current_user, require_admin


# ---------------------------------------------------------------------------
# UT-AUTH-001: CurrentUser dataclass
# ---------------------------------------------------------------------------


class TestCurrentUser:
    """CurrentUser correctly reports admin status based on roles."""

    def test_employee_is_not_admin(self) -> None:
        """UT-AUTH-001a: Employee role → is_admin is False."""
        user = CurrentUser(
            user_id="u1",
            email="emp@acme.com",
            first_name="Jane",
            last_name="Doe",
            roles=["Employee"],
        )
        assert user.is_admin is False

    def test_admin_role_is_admin(self) -> None:
        """UT-AUTH-001b: Admin role → is_admin is True."""
        user = CurrentUser(
            user_id="u2",
            email="admin@acme.com",
            first_name="Admin",
            last_name="User",
            roles=["Admin"],
        )
        assert user.is_admin is True

    def test_multiple_roles_with_admin(self) -> None:
        """UT-AUTH-001c: Multiple roles including Admin → is_admin is True."""
        user = CurrentUser(
            user_id="u3",
            email="both@acme.com",
            first_name="Both",
            last_name="Roles",
            roles=["Employee", "Admin"],
        )
        assert user.is_admin is True

    def test_empty_roles_is_not_admin(self) -> None:
        """UT-AUTH-001d: Empty roles → is_admin is False."""
        user = CurrentUser(
            user_id="u4",
            email="none@acme.com",
            first_name="No",
            last_name="Role",
            roles=[],
        )
        assert user.is_admin is False


# ---------------------------------------------------------------------------
# UT-AUTH-002: get_current_user dependency — missing credentials returns 401
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    """get_current_user returns 401 when no bearer token is provided."""

    @pytest.mark.asyncio
    async def test_missing_auth_header_returns_401(self) -> None:
        """UT-AUTH-002: No Authorization header → 401."""
        app = FastAPI()

        @app.get("/protected")
        async def _protected(user: CurrentUser = pytest.importorskip("fastapi").Depends(get_current_user)) -> dict:  # noqa: E501
            return {"user": user.email}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/protected")

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# UT-AUTH-003: require_admin dependency — employee returns 403
# ---------------------------------------------------------------------------


class TestRequireAdmin:
    """require_admin returns 403 when user lacks Admin role."""

    @pytest.mark.asyncio
    async def test_employee_gets_403_on_admin_endpoint(self) -> None:
        """UT-AUTH-003: Employee calling admin endpoint → 403 Forbidden."""
        app = FastAPI()

        employee = CurrentUser(
            user_id="u1",
            email="emp@acme.com",
            first_name="Jane",
            last_name="Doe",
            roles=["Employee"],
        )
        app.dependency_overrides[get_current_user] = lambda: employee

        @app.get("/admin-only")
        async def _admin_only(user: CurrentUser = pytest.importorskip("fastapi").Depends(require_admin)) -> dict:  # noqa: E501
            return {"user": user.email}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/admin-only")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_gets_200_on_admin_endpoint(self) -> None:
        """UT-AUTH-003b: Admin calling admin endpoint → allowed."""
        app = FastAPI()

        admin = CurrentUser(
            user_id="u2",
            email="admin@acme.com",
            first_name="Admin",
            last_name="User",
            roles=["Admin"],
        )
        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[require_admin] = lambda: admin

        @app.get("/admin-only")
        async def _admin_only(user: CurrentUser = pytest.importorskip("fastapi").Depends(require_admin)) -> dict:  # noqa: E501
            return {"user": user.email}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/admin-only")

        assert response.status_code == 200
