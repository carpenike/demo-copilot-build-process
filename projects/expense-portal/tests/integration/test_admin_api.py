"""Integration tests for admin panel endpoints.

Covers: FR-013, FR-024
User stories: US-009
Security: Admin access control (403 for non-admin)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from conftest import make_employee


def _build_admin_app(current_user, db_mock):
    from fastapi import FastAPI
    from starlette.middleware.sessions import SessionMiddleware

    from app.api.admin import router
    from app.api.dependencies import get_current_user, get_db, require_role

    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_mock
    app.dependency_overrides[require_role("finance_admin")] = lambda: current_user
    return app


# ====================================================================
# US-009 scenario 4: Non-admin access denied
# ====================================================================


class TestAdminAccessControl:
    """SEC: Non-admin user denied access to admin panel (US-009 scenario 4)."""

    @pytest.mark.asyncio
    async def test_employee_cannot_access_admin(self):
        """Non-finance-admin user gets 403 on admin endpoints."""
        from app.api.dependencies import get_current_user, get_db

        from fastapi import FastAPI
        from starlette.middleware.sessions import SessionMiddleware
        from app.api.admin import router

        user = make_employee(role="employee", direct_reports=[])

        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: user
        # Don't override require_role — let it check and reject

        db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/admin/categories")

        assert response.status_code == 403


# ====================================================================
# FR-024 + US-009: Category management
# ====================================================================


class TestCategoryManagement:
    """IT-ADM-001, IT-ADM-002: Create and update categories."""

    @pytest.mark.asyncio
    async def test_create_category_success(self):
        """IT-ADM-001: Create expense category (US-009 scenario 1)."""
        admin = make_employee(role="finance_admin")
        db = AsyncMock()

        # Mock duplicate check (no existing category)
        check_result = AsyncMock()
        check_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=check_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        app = _build_admin_app(admin, db)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/v1/admin/categories", json={
                "name": "Meals",
                "daily_limit": 75.00,
                "reimbursable": True,
                "per_diem_rates": [
                    {"destination": "US-Domestic", "rate": 75.00},
                ],
            })

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Meals"

    @pytest.mark.asyncio
    async def test_create_duplicate_category_returns_409(self):
        """IT-ADM: Duplicate category name returns 409 (ERR-010)."""
        admin = make_employee(role="finance_admin")
        db = AsyncMock()

        # Mock: category already exists
        existing = MagicMock()
        existing.name = "Meals"
        check_result = AsyncMock()
        check_result.scalar_one_or_none.return_value = existing
        db.execute = AsyncMock(return_value=check_result)

        app = _build_admin_app(admin, db)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/v1/admin/categories", json={
                "name": "Meals",
            })

        assert response.status_code == 409


# ====================================================================
# FR-024 + US-009: Threshold management
# ====================================================================


class TestThresholdManagement:
    """IT-ADM-003: Update approval thresholds (US-009 scenario 3)."""

    @pytest.mark.asyncio
    async def test_get_thresholds_with_no_config(self):
        """Returns defaults when no threshold row exists."""
        admin = make_employee(role="finance_admin")
        db = AsyncMock()

        result = AsyncMock()
        result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result)

        app = _build_admin_app(admin, db)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/admin/approval-thresholds")

        assert response.status_code == 200
        data = response.json()
        assert data["finance_review_threshold"] == 500.00
        assert data["auto_escalation_days"] == 5
        assert data["reminder_days"] == 3
