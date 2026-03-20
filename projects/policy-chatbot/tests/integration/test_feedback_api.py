"""Integration tests for POST /v1/feedback.

Covers: FR-028, FR-030
User Stories: US-007
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.feedback import router
from conftest import (
    build_test_app,
    make_employee_user,
    make_feedback,
    make_message,
    make_mock_db,
    make_mock_services,
    make_user_record,
    mock_db_scalar_result,
)


def _build_feedback_app(user=None, db=None, services=None):
    user = user or make_employee_user()
    db = db or make_mock_db()
    services = services or make_mock_services()
    return build_test_app(router, current_user=user, mock_db=db, services=services)


# ---------------------------------------------------------------------------
# IT-FB-001: Submit positive feedback (FR-028)
# ---------------------------------------------------------------------------


class TestSubmitFeedback:
    """POST /v1/feedback records thumbs-up/thumbs-down ratings."""

    @pytest.mark.asyncio
    async def test_submit_positive_feedback(self) -> None:
        """IT-FB-001: Positive feedback returns 201."""
        user = make_employee_user()
        db = make_mock_db()

        user_record = make_user_record(email=user.email)
        message = make_message()
        message_id = message.id

        db.execute.side_effect = [
            mock_db_scalar_result(user_record),  # _ensure_user
            mock_db_scalar_result(message),      # verify message exists
            mock_db_scalar_result(None),          # no duplicate feedback
        ]

        app = _build_feedback_app(user=user, db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/feedback",
                json={
                    "message_id": str(message_id),
                    "rating": "positive",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == "positive"
        assert data["message_id"] == str(message_id)

    @pytest.mark.asyncio
    async def test_submit_negative_feedback_with_comment(self) -> None:
        """IT-FB-002: Negative feedback with comment returns 201."""
        user = make_employee_user()
        db = make_mock_db()

        user_record = make_user_record(email=user.email)
        message = make_message()
        message_id = message.id

        db.execute.side_effect = [
            mock_db_scalar_result(user_record),  # _ensure_user
            mock_db_scalar_result(message),      # verify message exists
            mock_db_scalar_result(None),          # no duplicate feedback
        ]

        app = _build_feedback_app(user=user, db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/feedback",
                json={
                    "message_id": str(message_id),
                    "rating": "negative",
                    "comment": "This answer is outdated",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == "negative"
        assert data["comment"] == "This answer is outdated"

    @pytest.mark.asyncio
    async def test_duplicate_feedback_returns_409(self) -> None:
        """IT-FB-003: Duplicate feedback for same message returns 409."""
        user = make_employee_user()
        db = make_mock_db()

        user_record = make_user_record(email=user.email)
        message = make_message()
        existing_feedback = make_feedback(message_id=message.id)

        db.execute.side_effect = [
            mock_db_scalar_result(user_record),       # _ensure_user
            mock_db_scalar_result(message),            # verify message exists
            mock_db_scalar_result(existing_feedback),  # duplicate found
        ]

        app = _build_feedback_app(user=user, db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/feedback",
                json={
                    "message_id": str(message.id),
                    "rating": "positive",
                },
            )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_feedback_message_not_found_returns_404(self) -> None:
        """ERR-005: Feedback for non-existent message returns 404."""
        user = make_employee_user()
        db = make_mock_db()

        user_record = make_user_record(email=user.email)

        db.execute.side_effect = [
            mock_db_scalar_result(user_record),  # _ensure_user
            mock_db_scalar_result(None),          # message not found
        ]

        app = _build_feedback_app(user=user, db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/feedback",
                json={
                    "message_id": str(uuid.uuid4()),
                    "rating": "positive",
                },
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_rating_returns_422(self) -> None:
        """ERR-004: Invalid rating value returns 422."""
        app = _build_feedback_app()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/feedback",
                json={
                    "message_id": str(uuid.uuid4()),
                    "rating": "neutral",
                },
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_feedback_unauthenticated_returns_401(self) -> None:
        """SEC-002: Unauthenticated feedback → 401."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/feedback",
                json={
                    "message_id": str(uuid.uuid4()),
                    "rating": "positive",
                },
            )

        assert response.status_code == 401
