"""Integration tests for POST /v1/chat and POST /v1/chat/escalate.

Covers: FR-007, FR-008, FR-012, FR-013, FR-014, FR-015, FR-016, FR-025, FR-026
User Stories: US-001, US-005, US-006
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.chat import router
from conftest import (
    build_test_app,
    make_admin_user,
    make_conversation,
    make_employee_user,
    make_mock_db,
    make_mock_services,
    make_user_record,
    mock_db_scalar_result,
)


def _build_chat_app(
    user=None,
    db=None,
    services=None,
):
    """Build a test app with the chat router."""
    user = user or make_employee_user()
    db = db or make_mock_db()
    services = services or make_mock_services()
    return build_test_app(router, current_user=user, mock_db=db, services=services)


# ---------------------------------------------------------------------------
# IT-CHAT-001: POST /v1/chat — Happy path (FR-007, FR-015)
# ---------------------------------------------------------------------------


class TestChatEndpoint:
    """POST /v1/chat sends a message and gets a policy-grounded response."""

    @pytest.mark.asyncio
    async def test_chat_returns_200_with_response(self) -> None:
        """IT-CHAT-001: Valid message returns conversation_id, message_id, response."""
        user = make_employee_user()
        db = make_mock_db()
        services = make_mock_services()

        user_record = make_user_record(email=user.email)
        # _ensure_user: first query returns user, subsequent queries return conversation etc.
        conversation_mock = make_conversation(user_id=user_record.id)
        msg_mock = MagicMock(id=uuid.uuid4())

        db.execute.side_effect = [
            mock_db_scalar_result(user_record),  # _ensure_user
            mock_db_scalar_result(None),          # this won't be hit for new convo
        ]
        db.flush = AsyncMock()

        app = _build_chat_app(user=user, db=db, services=services)

        with patch("app.api.chat.orchestrate_chat", new_callable=AsyncMock) as mock_rag:
            mock_rag.return_value = {
                "response_type": "answer",
                "content": "Bereavement leave provides up to 5 days...",
                "citations": [
                    {
                        "document_title": "HR-POL-042",
                        "section": "Section 3.1",
                        "effective_date": "2025-09-01",
                    }
                ],
                "intent": {"type": "factual", "domain": "HR", "confidence": 0.94},
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/v1/chat",
                    json={"message": "What is the bereavement leave policy?"},
                )

        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "message_id" in data
        assert data["response"]["type"] == "answer"
        assert "disclaimer" in data["response"]

    @pytest.mark.asyncio
    async def test_chat_with_existing_conversation(self) -> None:
        """IT-CHAT-001b: Providing a valid conversation_id continues the session."""
        user = make_employee_user()
        db = make_mock_db()
        services = make_mock_services()

        user_record = make_user_record(email=user.email)
        conv_id = uuid.uuid4()
        conversation = make_conversation(id=conv_id, user_id=user_record.id)

        db.execute.side_effect = [
            mock_db_scalar_result(user_record),  # _ensure_user
            mock_db_scalar_result(conversation),  # find conversation
        ]

        app = _build_chat_app(user=user, db=db, services=services)

        with patch("app.api.chat.orchestrate_chat", new_callable=AsyncMock) as mock_rag:
            mock_rag.return_value = {
                "response_type": "answer",
                "content": "Follow-up answer...",
                "citations": [],
                "intent": {"type": "factual", "domain": "HR", "confidence": 0.90},
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/v1/chat",
                    json={
                        "conversation_id": str(conv_id),
                        "message": "What about for part-time employees?",
                    },
                )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_conversation_not_found_returns_404(self) -> None:
        """IT-CHAT-001c: Invalid conversation_id returns 404."""
        user = make_employee_user()
        db = make_mock_db()
        services = make_mock_services()

        user_record = make_user_record(email=user.email)

        db.execute.side_effect = [
            mock_db_scalar_result(user_record),  # _ensure_user
            mock_db_scalar_result(None),          # conversation not found
        ]

        app = _build_chat_app(user=user, db=db, services=services)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/chat",
                json={
                    "conversation_id": str(uuid.uuid4()),
                    "message": "Hello",
                },
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_chat_empty_message_returns_422(self) -> None:
        """ERR-001: Empty message body returns 422 validation error."""
        app = _build_chat_app()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/v1/chat", json={"message": ""})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_message_too_long_returns_422(self) -> None:
        """ERR-002: Message exceeding 2000 chars returns 422."""
        app = _build_chat_app()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/chat", json={"message": "x" * 2001}
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_unauthenticated_returns_401(self) -> None:
        """SEC-001: No auth header → 401."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        # No dependency override for get_current_user → real dep requires token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/chat", json={"message": "Hello"}
            )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# IT-ESC-001: POST /v1/chat/escalate (FR-025, FR-026, US-005)
# ---------------------------------------------------------------------------


class TestEscalateEndpoint:
    """POST /v1/chat/escalate initiates a handoff to live agent."""

    @pytest.mark.asyncio
    async def test_escalate_creates_ticket(self) -> None:
        """IT-ESC-001: Valid escalation returns ticket_id."""
        user = make_employee_user()
        db = make_mock_db()
        services = make_mock_services()

        user_record = make_user_record(email=user.email)
        conv_id = uuid.uuid4()
        conversation = make_conversation(id=conv_id, user_id=user_record.id)

        db.execute.side_effect = [
            mock_db_scalar_result(user_record),  # _ensure_user
            mock_db_scalar_result(conversation),  # find conversation
        ]

        app = _build_chat_app(user=user, db=db, services=services)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/chat/escalate",
                json={"conversation_id": str(conv_id)},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["escalation"]["status"] == "initiated"
        assert "ticket_id" in data["escalation"]

    @pytest.mark.asyncio
    async def test_escalate_conversation_not_found_returns_404(self) -> None:
        """ERR-003: Non-existent conversation → 404."""
        user = make_employee_user()
        db = make_mock_db()
        services = make_mock_services()

        user_record = make_user_record(email=user.email)

        db.execute.side_effect = [
            mock_db_scalar_result(user_record),  # _ensure_user
            mock_db_scalar_result(None),          # conversation not found
        ]

        app = _build_chat_app(user=user, db=db, services=services)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/chat/escalate",
                json={"conversation_id": str(uuid.uuid4())},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_escalate_unauthenticated_returns_401(self) -> None:
        """SEC-001: Unauthenticated escalation → 401."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/v1/chat/escalate",
                json={"conversation_id": str(uuid.uuid4())},
            )

        assert response.status_code == 401
