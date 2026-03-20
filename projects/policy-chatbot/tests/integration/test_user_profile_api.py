"""Integration tests for GET /v1/me — user profile endpoint.

Covers: FR-011
User Stories: US-011
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.chat import router
from conftest import (
    build_test_app,
    make_employee_user,
    make_mock_db,
    make_mock_services,
    make_user_record,
    mock_db_scalar_result,
)


def _build_profile_app(user=None, db=None):
    user = user or make_employee_user()
    db = db or make_mock_db()
    services = make_mock_services()
    return build_test_app(router, current_user=user, mock_db=db, services=services)


# ---------------------------------------------------------------------------
# IT-PROF-001: GET /v1/me (FR-011, US-011)
# ---------------------------------------------------------------------------


class TestUserProfile:
    """GET /v1/me retrieves the authenticated user's profile."""

    @pytest.mark.asyncio
    async def test_get_profile_returns_user_data(self) -> None:
        """IT-PROF-001: Profile includes first name, department, location."""
        user = make_employee_user(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@acme.com",
        )
        db = make_mock_db()

        user_record = make_user_record(
            email="jane.smith@acme.com",
            first_name="Jane",
            last_name="Smith",
            department="Engineering",
            location="HQ Campus",
            manager_email="manager@acme.com",
        )

        db.execute.return_value = mock_db_scalar_result(user_record)

        app = _build_profile_app(user=user, db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/me")

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jane"
        assert data["last_name"] == "Smith"
        assert data["email"] == "jane.smith@acme.com"
        assert data["department"] == "Engineering"
        assert data["location"] == "HQ Campus"
        assert data["manager"] == "manager@acme.com"

    @pytest.mark.asyncio
    async def test_get_profile_unauthenticated_returns_401(self) -> None:
        """Profile requires authentication — 401 without token."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/me")

        assert response.status_code == 401
