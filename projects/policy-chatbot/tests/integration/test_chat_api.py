"""Integration tests for the Chat API endpoints.

Tests derived from wireframe-spec.md and user stories US-001, US-006, US-014.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest
from fastapi.testclient import TestClient

from tests.conftest import make_admin_user, make_employee_user


class TestCreateConversation:
    """POST /v1/chat/conversations — start a new conversation session."""

    def test_create_conversation_web_channel(
        self, employee_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """IT-CHAT-001: Employee can create a conversation via web channel."""
        # Mock the conversation object returned after commit
        mock_conv = MagicMock()
        mock_conv.id = uuid.uuid4()
        mock_conv.started_at = datetime.now(tz=UTC)
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", mock_conv.id) or setattr(obj, "started_at", mock_conv.started_at)

        response = employee_client.post(
            "/v1/chat/conversations",
            json={"channel": "web"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "conversation_id" in data
        assert "greeting" in data
        assert "Alex" in data["greeting"]  # FR-011: personalized greeting
        assert data["user_context"]["display_name"] == "Alex Johnson"

    def test_create_conversation_teams_channel(
        self, employee_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """IT-CHAT-002: Employee can create a conversation via teams channel."""
        mock_conv = MagicMock()
        mock_conv.id = uuid.uuid4()
        mock_conv.started_at = datetime.now(tz=UTC)
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", mock_conv.id) or setattr(obj, "started_at", mock_conv.started_at)

        response = employee_client.post(
            "/v1/chat/conversations",
            json={"channel": "teams"},
        )

        assert response.status_code == 201

    def test_create_conversation_invalid_channel(
        self, employee_client: TestClient
    ) -> None:
        """Edge case: invalid channel value returns 422."""
        response = employee_client.post(
            "/v1/chat/conversations",
            json={"channel": "slack"},
        )

        assert response.status_code == 422

    def test_greeting_includes_user_name(
        self, employee_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """IT-CHAT-003: Greeting includes the employee's first name (FR-011)."""
        mock_conv = MagicMock()
        mock_conv.id = uuid.uuid4()
        mock_conv.started_at = datetime.now(tz=UTC)
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", mock_conv.id) or setattr(obj, "started_at", mock_conv.started_at)

        response = employee_client.post(
            "/v1/chat/conversations",
            json={"channel": "web"},
        )

        data = response.json()
        assert "Alex" in data["greeting"]


class TestSendMessage:
    """POST /v1/chat/conversations/{id}/messages — send message and get response."""

    def test_send_message_returns_response(
        self,
        employee_client: TestClient,
        mock_db: AsyncMock,
        mock_rag_pipeline: AsyncMock,
    ) -> None:
        """Employee can send a message and receive a chatbot response."""
        conv_id = uuid.uuid4()
        # Mock the conversation lookup
        mock_conv = MagicMock()
        mock_conv.id = conv_id
        mock_conv.user_id = "user-emp-001"
        mock_conv.last_activity_at = datetime.now(tz=UTC)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_db.execute.return_value = mock_result

        # Mock the message after commit
        mock_msg = MagicMock()
        mock_msg.id = uuid.uuid4()
        mock_msg.created_at = datetime.now(tz=UTC)
        mock_db.refresh.side_effect = lambda obj: (
            setattr(obj, "id", mock_msg.id),
            setattr(obj, "created_at", mock_msg.created_at),
        )

        response = employee_client.post(
            f"/v1/chat/conversations/{conv_id}/messages",
            json={"content": "What is the PTO policy?"},
        )

        assert response.status_code == 200

    def test_send_empty_message_rejected(
        self, employee_client: TestClient
    ) -> None:
        """Edge case: empty message content returns 422."""
        conv_id = uuid.uuid4()
        response = employee_client.post(
            f"/v1/chat/conversations/{conv_id}/messages",
            json={"content": ""},
        )

        assert response.status_code == 422

    def test_conversation_not_found(
        self, employee_client: TestClient, mock_db: AsyncMock
    ) -> None:
        """IT-CHAT-004: Accessing non-existent or another user's conversation returns 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        conv_id = uuid.uuid4()
        response = employee_client.post(
            f"/v1/chat/conversations/{conv_id}/messages",
            json={"content": "Hello"},
        )

        assert response.status_code == 404


class TestAuthBoundary:
    """NFR-007, NFR-010: Authentication and authorization boundaries."""

    def test_unauthenticated_request_returns_401(
        self, unauthenticated_client: TestClient
    ) -> None:
        """IT-AUTH-001: Request without token returns 401."""
        response = unauthenticated_client.post(
            "/v1/chat/conversations",
            json={"channel": "web"},
        )

        # FastAPI HTTPBearer returns 403 when no credentials provided
        assert response.status_code in (401, 403)
