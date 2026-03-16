"""Integration tests for the feedback API endpoint.

Tests derived from wireframe-spec.md and user stories US-005.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestFeedback:
    """FR-028: Submit feedback on a chatbot response."""

    def test_submit_positive_feedback(
        self,
        employee_client: TestClient,
        mock_db: AsyncMock,
    ) -> None:
        """IT-FB-001: Employee submits positive feedback."""
        conv_id = uuid.uuid4()
        msg_id = uuid.uuid4()

        # Mock message lookup
        mock_msg = MagicMock()
        mock_msg.id = msg_id
        mock_msg.metadata_ = {"intent": "pto_policy"}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_msg
        mock_db.execute.return_value = mock_result

        mock_feedback = MagicMock()
        mock_feedback.id = uuid.uuid4()
        mock_feedback.created_at = datetime.now(tz=UTC)
        mock_db.refresh.side_effect = lambda obj: (
            setattr(obj, "id", mock_feedback.id),
            setattr(obj, "created_at", mock_feedback.created_at),
        )

        response = employee_client.post(
            f"/v1/chat/conversations/{conv_id}/messages/{msg_id}/feedback",
            json={"rating": "positive"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "feedback_id" in data

    def test_submit_negative_feedback_with_comment(
        self,
        employee_client: TestClient,
        mock_db: AsyncMock,
    ) -> None:
        """IT-FB-002: Employee submits negative feedback with optional comment."""
        conv_id = uuid.uuid4()
        msg_id = uuid.uuid4()

        mock_msg = MagicMock()
        mock_msg.id = msg_id
        mock_msg.metadata_ = {"intent": "bereavement_leave"}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_msg
        mock_db.execute.return_value = mock_result

        mock_feedback = MagicMock()
        mock_feedback.id = uuid.uuid4()
        mock_feedback.created_at = datetime.now(tz=UTC)
        mock_db.refresh.side_effect = lambda obj: (
            setattr(obj, "id", mock_feedback.id),
            setattr(obj, "created_at", mock_feedback.created_at),
        )

        response = employee_client.post(
            f"/v1/chat/conversations/{conv_id}/messages/{msg_id}/feedback",
            json={
                "rating": "negative",
                "comment": "The answer didn't cover in-laws",
            },
        )

        assert response.status_code == 201

    def test_feedback_invalid_rating(
        self, employee_client: TestClient
    ) -> None:
        """Edge case: invalid rating value returns 422."""
        conv_id = uuid.uuid4()
        msg_id = uuid.uuid4()

        response = employee_client.post(
            f"/v1/chat/conversations/{conv_id}/messages/{msg_id}/feedback",
            json={"rating": "neutral"},
        )

        assert response.status_code == 422

    def test_feedback_message_not_found(
        self,
        employee_client: TestClient,
        mock_db: AsyncMock,
    ) -> None:
        """Edge case: feedback on non-existent message returns 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = employee_client.post(
            f"/v1/chat/conversations/{uuid.uuid4()}/messages/{uuid.uuid4()}/feedback",
            json={"rating": "positive"},
        )

        assert response.status_code == 404

    def test_feedback_comment_too_long(
        self, employee_client: TestClient
    ) -> None:
        """Edge case: comment exceeding max length is rejected."""
        conv_id = uuid.uuid4()
        msg_id = uuid.uuid4()

        response = employee_client.post(
            f"/v1/chat/conversations/{conv_id}/messages/{msg_id}/feedback",
            json={
                "rating": "negative",
                "comment": "x" * 2001,
            },
        )

        assert response.status_code == 422
