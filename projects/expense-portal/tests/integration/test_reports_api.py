"""Integration tests for dashboard and reporting endpoints.

Covers: FR-019, FR-020, FR-021
User stories: US-012, US-013
Security: SEC-011 (non-finance user denied)
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from conftest import make_cost_center, make_employee


def _build_reports_app(current_user, db_mock, role_override=None):
    from fastapi import FastAPI
    from starlette.middleware.sessions import SessionMiddleware

    from app.api.reports import router
    from app.api.dependencies import get_current_user, get_db, require_role

    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_mock

    if role_override:
        app.dependency_overrides[require_role(role_override)] = lambda: current_user

    return app


# ====================================================================
# SEC-011: Non-finance user denied access to finance dashboard
# ====================================================================


class TestFinanceDashboardPermissions:
    """SEC-011: Non-finance user cannot access finance reporting."""

    @pytest.mark.asyncio
    async def test_employee_cannot_access_finance_dashboard(self):
        """SEC-011: Regular employee gets 403 on finance endpoint (US-012)."""
        from app.api.dependencies import get_current_user, get_db, require_role

        from fastapi import FastAPI
        from starlette.middleware.sessions import SessionMiddleware
        from app.api.reports import router

        user = make_employee(role="employee", direct_reports=[])

        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: user
        # Don't override require_role — let it check and reject

        db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/reports/finance?period=monthly")

        assert response.status_code == 403


# ====================================================================
# FR-021 + US-012: CSV export
# ====================================================================


class TestCSVExport:
    """IT-RPT-004: CSV export for finance dashboard (FR-021)."""

    @pytest.mark.asyncio
    async def test_finance_csv_export_returns_csv_content_type(self):
        """IT-RPT-004: format=csv returns text/csv (US-012 scenario 3)."""
        from app.api.dependencies import get_current_user, get_db, require_role

        from fastapi import FastAPI
        from starlette.middleware.sessions import SessionMiddleware
        from app.api.reports import router

        user = make_employee(role="finance_reviewer")

        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: user
        # Override role check to pass
        app.dependency_overrides[require_role("finance_reviewer")] = lambda: user

        # Mock DB queries
        db = AsyncMock()
        summary_result = AsyncMock()
        summary_result.one.return_value = (Decimal("245000.00"), 312)
        cc_result = AsyncMock()
        cc_result.all.return_value = [("Engineering", Decimal("89000"), 120)]
        cat_result = AsyncMock()
        cat_result.all.return_value = [("Meals", Decimal("45000"), 380)]
        status_result = AsyncMock()
        status_result.all.return_value = [("approved", Decimal("200000"), 265)]

        call_count = {"n": 0}

        async def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return summary_result
            elif call_count["n"] == 2:
                return cc_result
            elif call_count["n"] == 3:
                return cat_result
            else:
                return status_result

        db.execute = AsyncMock(side_effect=execute_side_effect)
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/reports/finance?period=monthly&format=csv")

        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

# ====================================================================
# US-013: Manager can only see own team data
# ====================================================================


class TestManagerDashboardPermissions:
    """IT-RPT-003: Manager dashboard shows only direct reports (US-013)."""

    @pytest.mark.asyncio
    async def test_non_manager_gets_403(self):
        """Regular employee without direct reports gets 403 on manager dashboard."""
        from app.api.dependencies import get_current_user, get_db, require_role

        from fastapi import FastAPI
        from starlette.middleware.sessions import SessionMiddleware
        from app.api.reports import router

        user = make_employee(role="employee", direct_reports=[])

        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: user
        # Don't override require_role — let it deny

        db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/reports/manager")

        assert response.status_code == 403
