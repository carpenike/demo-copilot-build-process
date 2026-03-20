"""Integration tests for GET /v1/conversations and GET /v1/conversations/{id}.

Covers: NFR-010 (users see only their own conversations)
User Stories: US-002 (conversation history)
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.chat import router
from conftest import (
    build_test_app,
    make_conversation,
    make_employee_user,
    make_message,
    make_mock_db,
    make_mock_services,
    make_user_record,
    mock_db_scalar_result,
)


def _build_conv_app(user=None, db=None, services=None):
    user = user or make_employee_user()
    db = db or make_mock_db()
    services = services or make_mock_services()
    return build_test_app(router, current_user=user, mock_db=db, services=services)


# ---------------------------------------------------------------------------
# IT-CONV-001: GET /v1/conversations (listing)
# ---------------------------------------------------------------------------


class TestListConversations:
    """GET /v1/conversations lists the current user's recent conversations."""

    @pytest.mark.asyncio
    async def test_list_conversations_returns_200(self) -> None:
        """IT-CONV-001: Returns user's conversations."""
        user = make_employee_user()
        db = make_mock_db()

        user_record = make_user_record(email=user.email)
        conv = make_conversation(user_id=user_record.id)

        # _ensure_user
        result1 = mock_db_scalar_result(user_record)
        # list conversations
        result2 = AsyncMock()
        result2.scalars.return_value.all.return_value = [conv]
        # preview message
        result3 = mock_db_scalar_result("What is the PTO policy?")

        db.execute.side_effect = [result1, result2, result3]

        app = _build_conv_app(user=user, db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/conversations")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 1

    @pytest.mark.asyncio
    async def test_list_conversations_empty(self) -> None:
        """IT-CONV-001b: No conversations returns empty list."""
        user = make_employee_user()
        db = make_mock_db()

        user_record = make_user_record(email=user.email)

        result1 = mock_db_scalar_result(user_record)
        result2 = AsyncMock()
        result2.scalars.return_value.all.return_value = []

        db.execute.side_effect = [result1, result2]

        app = _build_conv_app(user=user, db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/conversations")

        assert response.status_code == 200
        assert response.json()["data"] == []


# ---------------------------------------------------------------------------
# IT-CONV-002: GET /v1/conversations/{id} (detail)
# ---------------------------------------------------------------------------


class TestGetConversation:
    """GET /v1/conversations/{id} retrieves full conversation history."""

    @pytest.mark.asyncio
    async def test_get_conversation_returns_messages(self) -> None:
        """IT-CONV-002: Returns conversation with message history."""
        user = make_employee_user()
        db = make_mock_db()

        user_record = make_user_record(email=user.email)
        conv_id = uuid.uuid4()
        conversation = make_conversation(id=conv_id, user_id=user_record.id)
        msg1 = make_message(conversation_id=conv_id, role="user", content="What is PTO?")
        msg2 = make_message(conversation_id=conv_id, role="assistant", content="PTO is...")

        # _ensure_user, find conversation, list messages
        db.execute.side_effect = [
            mock_db_scalar_result(user_record),
            mock_db_scalar_result(conversation),
            AsyncMock(scalars=lambda: MagicMock(all=lambda: [msg1, msg2])),
        ]

        # Fix the mock for scalars().all() pattern
        msg_result = AsyncMock()
        msg_result.scalars.return_value.all.return_value = [msg1, msg2]
        db.execute.side_effect = [
            mock_db_scalar_result(user_record),
            mock_db_scalar_result(conversation),
            msg_result,
        ]

        app = _build_conv_app(user=user, db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/v1/conversations/{conv_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(conv_id)
        assert len(data["messages"]) == 2

    @pytest.mark.asyncio
    async def test_get_conversation_not_found_returns_404(self) -> None:
        """SEC-005: Non-existent conversation returns 404."""
        user = make_employee_user()
        db = make_mock_db()

        user_record = make_user_record(email=user.email)

        db.execute.side_effect = [
            mock_db_scalar_result(user_record),  # _ensure_user
            mock_db_scalar_result(None),          # conversation not found
        ]

        app = _build_conv_app(user=user, db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/v1/conversations/{uuid.uuid4()}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_other_users_conversation_returns_403(self) -> None:
        """SEC-004: Accessing another user's conversation returns 403."""
        user = make_employee_user()
        db = make_mock_db()

        user_record = make_user_record(email=user.email)
        other_user_id = uuid.uuid4()
        conv_id = uuid.uuid4()
        conversation = make_conversation(id=conv_id, user_id=other_user_id)

        db.execute.side_effect = [
            mock_db_scalar_result(user_record),   # _ensure_user
            mock_db_scalar_result(conversation),   # found but belongs to other user
        ]

        app = _build_conv_app(user=user, db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/v1/conversations/{conv_id}")

        assert response.status_code == 403
