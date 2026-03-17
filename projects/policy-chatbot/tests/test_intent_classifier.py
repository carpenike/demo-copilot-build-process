"""Unit tests for intent classification (FR-008, FR-016).

Tests are derived from requirements, not implementation:
- FR-008: classify domain, query type (factual/procedural/sensitive)
- FR-016: detect confidential HR matters → immediate escalation
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.intent_classifier import IntentResult, classify_intent


@pytest.fixture()
def mock_llm() -> AsyncMock:
    """Create a mock LLM service for intent classification tests."""
    return AsyncMock()


class TestIntentClassification:
    """FR-008: Intent classification determines domain and query type."""

    async def test_factual_hr_query(self, mock_llm: AsyncMock) -> None:
        """UT-003: Factual HR query is classified correctly."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": "HR", "type": "factual", "reasoning": "policy question"}
        )

        result = await classify_intent(mock_llm, "What is the bereavement leave policy?")

        assert result.domain == "HR"
        assert result.intent_type == "factual"
        assert result.is_sensitive is False

    async def test_procedural_query(self, mock_llm: AsyncMock) -> None:
        """UT-004: Procedural query is classified as procedural."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": "HR", "type": "procedural", "reasoning": "how-to"}
        )

        result = await classify_intent(mock_llm, "How do I request FMLA leave?")

        assert result.intent_type == "procedural"
        assert result.is_sensitive is False

    async def test_it_domain_query(self, mock_llm: AsyncMock) -> None:
        """FR-008: IT domain query is classified to correct domain."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": "IT", "type": "factual", "reasoning": "IT policy"}
        )

        result = await classify_intent(mock_llm, "What is the VPN policy?")

        assert result.domain == "IT"
        assert result.intent_type == "factual"

    async def test_unknown_domain(self, mock_llm: AsyncMock) -> None:
        """FR-008: Unknown domain returns None."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": None, "type": "factual", "reasoning": "unclear"}
        )

        result = await classify_intent(mock_llm, "What is the meaning of life?")

        assert result.domain is None

    async def test_conversation_context_passed_to_llm(
        self, mock_llm: AsyncMock
    ) -> None:
        """FR-009: Conversation context is forwarded to the classifier."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": "HR", "type": "factual", "reasoning": "follow-up"}
        )
        context = [{"role": "user", "content": "What is the PTO policy?"}]

        await classify_intent(mock_llm, "What about for part-time?", context)

        mock_llm.classify_intent.assert_called_once_with(
            "What about for part-time?", context
        )


class TestSensitiveTopicDetection:
    """FR-016: Detect confidential HR matters → immediate escalation."""

    async def test_sensitive_via_llm_classification(
        self, mock_llm: AsyncMock
    ) -> None:
        """UT-009: LLM classifies query as sensitive."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": "HR", "type": "sensitive", "reasoning": "harassment"}
        )

        result = await classify_intent(
            mock_llm, "I want to report harassment in my team"
        )

        assert result.is_sensitive is True
        assert result.intent_type == "sensitive"

    async def test_sensitive_via_keyword_detection(
        self, mock_llm: AsyncMock
    ) -> None:
        """UT-009: Keyword-based sensitive detection as fallback."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": "HR", "type": "factual", "reasoning": "seems factual"}
        )

        result = await classify_intent(
            mock_llm, "How do I report discrimination?"
        )

        assert result.is_sensitive is True
        assert result.intent_type == "sensitive"

    async def test_whistleblower_detected(self, mock_llm: AsyncMock) -> None:
        """FR-016: Whistleblower query is detected as sensitive."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": "HR", "type": "factual", "reasoning": "test"}
        )

        result = await classify_intent(
            mock_llm, "I need to be a whistleblower about fraud"
        )

        assert result.is_sensitive is True

    async def test_non_sensitive_hr_query(self, mock_llm: AsyncMock) -> None:
        """UT-010: Normal HR query is not flagged as sensitive."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": "HR", "type": "factual", "reasoning": "standard"}
        )

        result = await classify_intent(mock_llm, "What's the dress code policy?")

        assert result.is_sensitive is False
        assert result.intent_type == "factual"

    async def test_retaliation_detected(self, mock_llm: AsyncMock) -> None:
        """FR-016: Retaliation keyword triggers sensitive detection."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": "HR", "type": "factual", "reasoning": "test"}
        )

        result = await classify_intent(
            mock_llm, "I'm experiencing retaliation from my manager"
        )

        assert result.is_sensitive is True
