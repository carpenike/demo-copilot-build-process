"""Integration tests for expense report and line item API endpoints.

Covers: FR-001, FR-002, FR-005, FR-006, FR-007
User stories: US-001, US-003, US-004
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from conftest import make_category, make_cost_center, make_employee, make_expense_report, make_line_item


# ---- Fixtures ----


def _build_test_app(current_user, db_mock):
    """Create a FastAPI test app with overridden dependencies."""
    from fastapi import FastAPI
    from starlette.middleware.sessions import SessionMiddleware

    from app.api.expenses import router
    from app.api.dependencies import get_current_user, get_db

    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    app.include_router(router)

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_mock

    return app


# ====================================================================
# FR-001 + US-001: Create expense report
# ====================================================================


class TestCreateReport:
    """IT-EXP-001, IT-EXP-002: Expense report creation."""

    @pytest.mark.asyncio
    async def test_create_report_success(self):
        """IT-EXP-001: Create report with valid fields (FR-001, US-001 scenario 1)."""
        user = make_employee()
        db = AsyncMock()

        # Mock count query and flush
        count_result = AsyncMock()
        count_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=count_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        app = _build_test_app(user, db)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/v1/expenses/reports", json={
                "title": "Q1 Client Meetings",
                "start_date": "2026-03-01",
                "end_date": "2026-03-07",
                "business_purpose": "Client meetings in Seattle",
            })

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Q1 Client Meetings"
        assert data["status"] == "draft"

    @pytest.mark.asyncio
    async def test_create_report_end_date_before_start_date(self):
        """IT-EXP-002: Reject when end_date < start_date (ERR-001)."""
        user = make_employee()
        db = AsyncMock()

        app = _build_test_app(user, db)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/v1/expenses/reports", json={
                "title": "Bad Dates",
                "start_date": "2026-03-07",
                "end_date": "2026-03-01",
                "business_purpose": "Testing",
            })

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_report_missing_required_field(self):
        """US-001 scenario 3: Missing required field → 422 validation error."""
        user = make_employee()
        db = AsyncMock()

        app = _build_test_app(user, db)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/v1/expenses/reports", json={
                "title": "Missing fields",
                # Missing start_date, end_date, business_purpose
            })

        assert response.status_code == 422


# ====================================================================
# FR-002 + US-001: Line items
# ====================================================================


class TestLineItems:
    """IT-EXP-003, IT-EXP-004: Line item endpoints."""

    @pytest.mark.asyncio
    async def test_add_line_item_invalid_currency(self):
        """IT-EXP-004: Reject line item with unsupported currency EUR (ERR-003)."""
        user = make_employee()
        db = AsyncMock()

        app = _build_test_app(user, db)
        report_id = uuid.uuid4()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/v1/expenses/reports/{report_id}/line-items",
                json={
                    "date": "2026-03-01",
                    "category": "Meals",
                    "vendor_name": "Test",
                    "amount": 42.50,
                    "currency": "EUR",  # Not allowed — only USD/CAD
                    "description": "Test",
                },
            )

        assert response.status_code == 422  # Pydantic validation


# ====================================================================
# FR-006 + US-001: Draft management
# ====================================================================


class TestDraftManagement:
    """IT-EXP-006: Save and retrieve draft (FR-006, US-001 scenario 2)."""

    @pytest.mark.asyncio
    async def test_draft_report_created_with_draft_status(self):
        """Draft reports are created with status='draft' by default."""
        user = make_employee()
        db = AsyncMock()

        count_result = AsyncMock()
        count_result.scalar.return_value = 5
        db.execute = AsyncMock(return_value=count_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        app = _build_test_app(user, db)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/v1/expenses/reports", json={
                "title": "My Draft",
                "start_date": "2026-03-01",
                "end_date": "2026-03-07",
                "business_purpose": "Will complete later",
                "submit": False,
            })

        assert response.status_code == 201
        assert response.json()["status"] == "draft"


# ====================================================================
# NFR-022: Cursor-based pagination
# ====================================================================


class TestPagination:
    """IT-EXP-008: Cursor-based pagination on list endpoints."""

    @pytest.mark.asyncio
    async def test_pagination_limit_enforced(self):
        """NFR-022: Limit parameter is respected and capped at 100."""
        user = make_employee()
        db = AsyncMock()

        # Mock empty result
        list_result = AsyncMock()
        list_result.scalars.return_value.all.return_value = []
        count_result = AsyncMock()
        count_result.scalar.return_value = 0

        call_count = {"n": 0}

        async def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return list_result
            return count_result

        db.execute = AsyncMock(side_effect=execute_side_effect)

        app = _build_test_app(user, db)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/expenses/reports?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "next_cursor" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_pagination_limit_above_max_rejected(self):
        """NFR-022: Limit > 100 is rejected."""
        user = make_employee()
        db = AsyncMock()

        app = _build_test_app(user, db)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/expenses/reports?limit=200")

        assert response.status_code == 422  # Query validation
