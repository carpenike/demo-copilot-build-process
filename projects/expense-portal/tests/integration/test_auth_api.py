"""Integration tests for authentication endpoints.

Covers: NFR-007
User stories: US-001 scenario 4 (unauthenticated access)
Security: SEC-001 (unauthenticated request → 401)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from conftest import make_employee


# ====================================================================
# SEC-001: Unauthenticated access denied
# ====================================================================


class TestAuthenticationRequired:
    """SEC-001: Unauthenticated requests receive 401 (NFR-007, US-001 scenario 4)."""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_to_expenses_returns_401(self):
        """SEC-001: No session → 401 on protected endpoint."""
        from fastapi import FastAPI
        from starlette.middleware.sessions import SessionMiddleware

        from app.api.expenses import router
        from app.models.database import get_db

        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(router)

        # Don't override get_current_user — let it check session and fail
        db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/expenses/reports")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthenticated_request_to_approvals_returns_401(self):
        """SEC-001: No session → 401 on approvals endpoint."""
        from fastapi import FastAPI
        from starlette.middleware.sessions import SessionMiddleware

        from app.api.approvals import router
        from app.models.database import get_db

        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(router)

        db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/approvals/pending")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthenticated_request_to_admin_returns_401(self):
        """SEC-001: No session → 401 on admin endpoint."""
        from fastapi import FastAPI
        from starlette.middleware.sessions import SessionMiddleware

        from app.api.admin import router
        from app.models.database import get_db

        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(router)

        db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/admin/categories")

        assert response.status_code == 401


# ====================================================================
# Auth flow endpoints (login, callback, logout)
# ====================================================================


class TestAuthEndpoints:
    """Auth routes return redirects as expected."""

    @pytest.mark.asyncio
    async def test_logout_without_session_still_redirects(self):
        """POST /v1/auth/logout clears session and redirects."""
        from fastapi import FastAPI
        from starlette.middleware.sessions import SessionMiddleware

        from app.api.auth import router

        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(router)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.post("/v1/auth/logout")

        assert response.status_code == 302
