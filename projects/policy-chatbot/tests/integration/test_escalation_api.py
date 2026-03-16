"""Integration tests for the escalation API endpoint.

Tests derived from wireframe-spec.md and user stories US-004.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestEscalation:
    """FR-025, FR-026: Escalate conversation to a live service desk agent."""

    def test_escalate_to_hr(
        self,
        employee_client: TestClient,
        mock_db: AsyncMock,
        mock_redis: AsyncMock,
        mock_servicenow: AsyncMock,
    ) -> None:
        """IT-ESC-001: Employee can escalate a conversation to HR."""
        conv_id = uuid.uuid4()
        mock_conv = MagicMock()
        mock_conv.id = conv_id
        mock_conv.user_id = "user-emp-001"
        mock_conv.status = "active"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_db.execute.return_value = mock_result

        mock_esc = MagicMock()
        mock_esc.id = uuid.uuid4()
        mock_esc.created_at = datetime.now(tz=UTC)
        mock_db.refresh.side_effect = lambda obj: (
            setattr(obj, "id", mock_esc.id),
            setattr(obj, "created_at", mock_esc.created_at),
        )

        response = employee_client.post(
            f"/v1/chat/conversations/{conv_id}/escalate",
            json={"target_team": "hr"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["servicenow_ticket_id"] == "INC0012345"
        assert "HR" in data["message"]

    def test_escalate_passes_transcript(
        self,
        employee_client: TestClient,
        mock_db: AsyncMock,
        mock_redis: AsyncMock,
        mock_servicenow: AsyncMock,
    ) -> None:
        """IT-ESC-002: Escalation passes conversation transcript to ServiceNow (FR-026)."""
        conv_id = uuid.uuid4()
        mock_conv = MagicMock()
        mock_conv.id = conv_id
        mock_conv.user_id = "user-emp-001"
        mock_conv.status = "active"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_db.execute.return_value = mock_result

        # Mock conversation history
        mock_redis.get_conversation_history.return_value = [
            {"role": "user", "content": "What is the PTO policy?"},
            {"role": "assistant", "content": "You get 20 days."},
        ]

        mock_esc = MagicMock()
        mock_esc.id = uuid.uuid4()
        mock_esc.created_at = datetime.now(tz=UTC)
        mock_db.refresh.side_effect = lambda obj: (
            setattr(obj, "id", mock_esc.id),
            setattr(obj, "created_at", mock_esc.created_at),
        )

        employee_client.post(
            f"/v1/chat/conversations/{conv_id}/escalate",
            json={"target_team": "it"},
        )

        # Verify ServiceNow was called with transcript
        mock_servicenow.create_escalation_ticket.assert_called_once()
        call_kwargs = mock_servicenow.create_escalation_ticket.call_args.kwargs
        assert "transcript_summary" in call_kwargs
        assert len(call_kwargs["transcript_summary"]) > 0

    def test_escalate_invalid_team(
        self, employee_client: TestClient
    ) -> None:
        """Edge case: invalid target_team returns 422."""
        conv_id = uuid.uuid4()
        response = employee_client.post(
            f"/v1/chat/conversations/{conv_id}/escalate",
            json={"target_team": "marketing"},
        )

        assert response.status_code == 422

    def test_escalate_nonexistent_conversation(
        self,
        employee_client: TestClient,
        mock_db: AsyncMock,
    ) -> None:
        """Edge case: escalating a non-existent conversation returns 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = employee_client.post(
            f"/v1/chat/conversations/{uuid.uuid4()}/escalate",
            json={"target_team": "hr"},
        )

        assert response.status_code == 404

    def test_escalate_updates_conversation_status(
        self,
        employee_client: TestClient,
        mock_db: AsyncMock,
        mock_redis: AsyncMock,
        mock_servicenow: AsyncMock,
    ) -> None:
        """Conversation status is updated to 'escalated' after handoff."""
        conv_id = uuid.uuid4()
        mock_conv = MagicMock()
        mock_conv.id = conv_id
        mock_conv.user_id = "user-emp-001"
        mock_conv.status = "active"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_conv
        mock_db.execute.return_value = mock_result

        mock_esc = MagicMock()
        mock_esc.id = uuid.uuid4()
        mock_esc.created_at = datetime.now(tz=UTC)
        mock_db.refresh.side_effect = lambda obj: (
            setattr(obj, "id", mock_esc.id),
            setattr(obj, "created_at", mock_esc.created_at),
        )

        employee_client.post(
            f"/v1/chat/conversations/{conv_id}/escalate",
            json={"target_team": "facilities"},
        )

        assert mock_conv.status == "escalated"
