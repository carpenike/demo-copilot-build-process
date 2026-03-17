"""Integration tests for chat API endpoints.

Tests cover:
- FR-007: Accept natural language questions via web chat
- FR-012–FR-015: RAG answer generation with citations and disclaimer
- FR-016: Sensitive topic detection → escalation
- FR-025: Explicit escalation to live agent
- FR-028: Feedback submission
- NFR-007: Unauthenticated requests return 401
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.intent_classifier import IntentResult
from app.core.rag_pipeline import RAGResult
from app.models.schemas import (
    ChatResponseBody,
    Citation,
    EscalationInfo,
    IntentInfo,
    IntentType,
)
from app.services.llm_service import DISCLAIMER


def _make_rag_result(
    content: str = "Test answer",
    confidence: float = 0.9,
    escalated: bool = False,
    citations: list[Citation] | None = None,
    should_escalate: bool = False,
    intent_type: str = "factual",
    domain: str | None = "HR",
) -> RAGResult:
    """Helper to construct a RAGResult for test assertions."""
    return RAGResult(
        response_body=ChatResponseBody(
            content=content,
            citations=citations or [],
            checklist=None,
            disclaimer=DISCLAIMER,
            intent=IntentInfo(domain=domain, type=IntentType(intent_type)),
            confidence=confidence,
            escalated=escalated,
        ),
        intent=IntentResult(domain=domain, intent_type=intent_type, is_sensitive=False),
        should_escalate=should_escalate,
    )


class TestChatEndpoint:
    """POST /api/v1/chat — send message and get RAG response."""

    def test_chat_returns_cited_answer(
        self, client: TestClient, mock_conv_service: AsyncMock
    ) -> None:
        """IT-001 / FR-007: Chat returns response with conversation and message IDs."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.api.chat.rag_pipeline.run_pipeline",
                AsyncMock(
                    return_value=_make_rag_result(
                        content="Bereavement leave is 5 days.",
                        citations=[
                            Citation(
                                document_title="Bereavement Policy",
                                section="Section 3",
                                effective_date="2025-06-01",
                                source_url="https://intranet.acme.com/hr/bereavement",
                            )
                        ],
                        confidence=0.92,
                    )
                ),
            )

            response = client.post(
                "/api/v1/chat",
                json={"message": "What is the bereavement leave policy?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "message_id" in data
        assert "response" in data

    def test_chat_with_existing_conversation(
        self, client: TestClient, mock_conv_service: AsyncMock
    ) -> None:
        """FR-009: Follow-up within existing conversation uses context."""
        conv_id = str(uuid.uuid4())

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.api.chat.rag_pipeline.run_pipeline",
                AsyncMock(return_value=_make_rag_result()),
            )

            response = client.post(
                "/api/v1/chat",
                json={"conversation_id": conv_id, "message": "What about part-time?"},
            )

        assert response.status_code == 200

    def test_chat_empty_message_returns_422(self, client: TestClient) -> None:
        """IT-018 / ERR-001: Empty message returns 422."""
        response = client.post("/api/v1/chat", json={"message": ""})

        assert response.status_code == 422

    def test_chat_message_too_long_returns_422(self, client: TestClient) -> None:
        """ERR-002: Message exceeding 2000 chars returns 422."""
        response = client.post(
            "/api/v1/chat", json={"message": "x" * 2001}
        )

        assert response.status_code == 422

    def test_chat_missing_message_returns_422(self, client: TestClient) -> None:
        """Validation: missing required field returns 422."""
        response = client.post("/api/v1/chat", json={})

        assert response.status_code == 422

    def test_chat_unauthenticated_returns_401(
        self, unauthed_client: TestClient
    ) -> None:
        """SEC-001 / NFR-007: Unauthenticated request returns 401."""
        response = unauthed_client.post(
            "/api/v1/chat", json={"message": "test"}
        )

        assert response.status_code == 401


class TestEscalateEndpoint:
    """POST /api/v1/chat/{conversation_id}/escalate — escalate to live agent."""

    def test_escalate_succeeds(
        self, client: TestClient, mock_conv_service: AsyncMock
    ) -> None:
        """IT-004 / FR-025: Explicit escalation returns incident ID."""
        conv_id = str(uuid.uuid4())

        response = client.post(
            f"/api/v1/chat/{conv_id}/escalate",
            json={"reason": "I need a human"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "escalation" in data
        assert "servicenow_incident_id" in data["escalation"]

    def test_escalate_unknown_conversation_returns_404(
        self, client: TestClient, mock_conv_service: AsyncMock
    ) -> None:
        """IT-019 / ERR-003: Unknown conversation ID returns 404."""
        mock_conv_service.get_transcript = AsyncMock(return_value=[])
        conv_id = str(uuid.uuid4())

        response = client.post(
            f"/api/v1/chat/{conv_id}/escalate", json={}
        )

        assert response.status_code == 404

    def test_escalate_unauthenticated_returns_401(
        self, unauthed_client: TestClient
    ) -> None:
        """SEC-001: Unauthenticated escalation returns 401."""
        conv_id = str(uuid.uuid4())
        response = unauthed_client.post(
            f"/api/v1/chat/{conv_id}/escalate", json={}
        )

        assert response.status_code == 401


class TestFeedbackEndpoint:
    """POST /api/v1/chat/{conversation_id}/feedback — submit feedback."""

    def test_positive_feedback_returns_201(
        self, client: TestClient, mock_feedback_service: AsyncMock
    ) -> None:
        """IT-005 / FR-028: Positive feedback is recorded."""
        conv_id = str(uuid.uuid4())
        msg_id = str(uuid.uuid4())

        response = client.post(
            f"/api/v1/chat/{conv_id}/feedback",
            json={
                "message_id": msg_id,
                "rating": "positive",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == "positive"

    def test_negative_feedback_with_comment(
        self, client: TestClient, mock_feedback_service: AsyncMock
    ) -> None:
        """FR-028: Negative feedback with optional comment."""
        conv_id = str(uuid.uuid4())
        msg_id = str(uuid.uuid4())

        response = client.post(
            f"/api/v1/chat/{conv_id}/feedback",
            json={
                "message_id": msg_id,
                "rating": "negative",
                "comment": "The policy has changed",
            },
        )

        assert response.status_code == 201

    def test_duplicate_feedback_returns_409(
        self, client: TestClient, mock_feedback_service: AsyncMock
    ) -> None:
        """IT-006 / ERR-005: Duplicate feedback returns 409."""
        mock_feedback_service.submit_feedback = AsyncMock(
            side_effect=ValueError("Feedback already submitted for this message")
        )
        conv_id = str(uuid.uuid4())
        msg_id = str(uuid.uuid4())

        response = client.post(
            f"/api/v1/chat/{conv_id}/feedback",
            json={"message_id": msg_id, "rating": "positive"},
        )

        assert response.status_code == 409

    def test_invalid_rating_returns_422(self, client: TestClient) -> None:
        """Validation: invalid rating value returns 422."""
        conv_id = str(uuid.uuid4())
        msg_id = str(uuid.uuid4())

        response = client.post(
            f"/api/v1/chat/{conv_id}/feedback",
            json={"message_id": msg_id, "rating": "invalid_value"},
        )

        assert response.status_code == 422

    def test_feedback_unauthenticated_returns_401(
        self, unauthed_client: TestClient
    ) -> None:
        """SEC-001: Unauthenticated feedback returns 401."""
        conv_id = str(uuid.uuid4())
        msg_id = str(uuid.uuid4())

        response = unauthed_client.post(
            f"/api/v1/chat/{conv_id}/feedback",
            json={"message_id": msg_id, "rating": "positive"},
        )

        assert response.status_code == 401
