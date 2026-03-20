"""Unit tests for the RAG orchestration pipeline (app/core/rag.py).

Covers: FR-008, FR-009, FR-012, FR-013, FR-014, FR-016, FR-027, NFR-006
User Stories: US-001, US-002, US-003, US-005, US-006
"""

from unittest.mock import AsyncMock

import pytest

from app.core.rag import (
    CONFIDENTIAL_KEYWORDS,
    DISCLAIMER,
    detect_confidential_topic,
    orchestrate_chat,
)


# ---------------------------------------------------------------------------
# UT-RAG-001: Confidential topic detection (FR-016, US-006)
# ---------------------------------------------------------------------------


class TestDetectConfidentialTopic:
    """detect_confidential_topic must recognize all keywords from FR-016."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "message",
        [
            "I want to report harassment",
            "How do I file a DISCRIMINATION complaint?",
            "I need to talk about whistleblower protection",
            "I'm experiencing retaliation from my manager",
            "This is a hostile work environment",
            "I want to report sexual harassment",
        ],
    )
    async def test_detects_confidential_keywords(self, message: str) -> None:
        """UT-RAG-001a: Each confidential keyword triggers detection."""
        result = await detect_confidential_topic(message)
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "message",
        [
            "What is the PTO policy?",
            "How do I request FMLA leave?",
            "What is the anti-harassment training schedule?",
            "Where is the HR office?",
            "How many vacation days do I have?",
        ],
    )
    async def test_does_not_flag_non_confidential(self, message: str) -> None:
        """UT-RAG-001b: General queries are NOT flagged as confidential."""
        result = await detect_confidential_topic(message)
        assert result is False

    async def test_keywords_set_is_not_empty(self) -> None:
        """Sanity check — the keyword set is populated."""
        assert len(CONFIDENTIAL_KEYWORDS) >= 5


# ---------------------------------------------------------------------------
# UT-RAG-002: Orchestrate chat — confidential topic path (FR-016)
# ---------------------------------------------------------------------------


class TestOrchestrateChatConfidential:
    """orchestrate_chat returns confidential_escalation for sensitive topics."""

    @pytest.mark.asyncio
    async def test_confidential_returns_escalation(self) -> None:
        """UT-RAG-002: Confidential topic skips RAG and returns escalation."""
        search = AsyncMock()
        openai = AsyncMock()
        redis = AsyncMock()

        result = await orchestrate_chat(
            message="I want to report harassment",
            conversation_id=None,
            user_id="user-1",
            user_email="user@acme.com",
            search_service=search,
            openai_service=openai,
            redis_service=redis,
        )

        assert result["response_type"] == "confidential_escalation"
        assert "escalation" in result
        assert result["escalation"]["team"] == "HR Confidential Support"
        # Search and OpenAI should NOT be called
        search.hybrid_search.assert_not_called()
        openai.generate_answer.assert_not_called()


# ---------------------------------------------------------------------------
# UT-RAG-003: Orchestrate chat — standard answer path (FR-008, FR-012, FR-013)
# ---------------------------------------------------------------------------


class TestOrchestrateChatStandardAnswer:
    """orchestrate_chat returns a grounded answer for non-confidential queries."""

    @pytest.mark.asyncio
    async def test_standard_answer_returned(self) -> None:
        """UT-RAG-003a: Normal query flows through classify → search → generate."""
        search = AsyncMock()
        search.hybrid_search.return_value = [
            {
                "document_title": "HR-POL-042",
                "section_heading": "Section 3.1",
                "content": "Bereavement leave provides up to 5 days...",
                "source_url": "https://intranet.acme.com/policies/HR-POL-042",
            }
        ]

        openai = AsyncMock()
        openai.classify_intent.return_value = {
            "type": "factual",
            "domain": "HR",
            "confidence": 0.94,
        }
        openai.generate_answer.return_value = {
            "content": "Bereavement leave provides up to 5 days of paid leave...",
            "citations": [
                {
                    "document_title": "HR-POL-042",
                    "section": "Section 3.1",
                    "effective_date": "2025-09-01",
                }
            ],
            "response_type": "answer",
        }

        redis = AsyncMock()
        redis.get_session.return_value = None

        result = await orchestrate_chat(
            message="What is the bereavement leave policy?",
            conversation_id=None,
            user_id="user-1",
            user_email="user@acme.com",
            search_service=search,
            openai_service=openai,
            redis_service=redis,
        )

        assert result["response_type"] == "answer"
        assert "citations" in result
        assert result["intent"]["type"] == "factual"
        search.hybrid_search.assert_called_once()
        openai.classify_intent.assert_called_once()
        openai.generate_answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_intent_domain_passed_to_search(self) -> None:
        """UT-RAG-003b: Classified domain filters the search query."""
        search = AsyncMock()
        search.hybrid_search.return_value = [{"content": "policy text"}]

        openai = AsyncMock()
        openai.classify_intent.return_value = {
            "type": "factual",
            "domain": "Finance",
            "confidence": 0.90,
        }
        openai.generate_answer.return_value = {
            "content": "Answer",
            "citations": [],
            "response_type": "answer",
        }

        redis = AsyncMock()
        redis.get_session.return_value = None

        await orchestrate_chat(
            message="What is the travel reimbursement limit?",
            conversation_id=None,
            user_id="user-1",
            user_email="user@acme.com",
            search_service=search,
            openai_service=openai,
            redis_service=redis,
        )

        search.hybrid_search.assert_called_once_with(
            "What is the travel reimbursement limit?",
            top_k=5,
            category_filter="Finance",
        )


# ---------------------------------------------------------------------------
# UT-RAG-004: Conversation context loading (FR-009, US-002)
# ---------------------------------------------------------------------------


class TestOrchestrateChatConversationContext:
    """orchestrate_chat loads conversation history from Redis for follow-ups."""

    @pytest.mark.asyncio
    async def test_loads_history_from_redis(self) -> None:
        """UT-RAG-004a: When conversation_id provided, history loaded from Redis."""
        search = AsyncMock()
        search.hybrid_search.return_value = [{"content": "PTO info"}]

        openai = AsyncMock()
        openai.classify_intent.return_value = {
            "type": "factual",
            "domain": "HR",
            "confidence": 0.88,
        }
        openai.generate_answer.return_value = {
            "content": "Part-time PTO...",
            "citations": [],
            "response_type": "answer",
        }

        prior_messages = [
            {"role": "user", "content": "What is the PTO policy?"},
            {"role": "assistant", "content": "PTO accrual is..."},
        ]
        redis = AsyncMock()
        redis.get_session.return_value = {"messages": prior_messages}

        await orchestrate_chat(
            message="What about for part-time employees?",
            conversation_id="conv-123",
            user_id="user-1",
            user_email="user@acme.com",
            search_service=search,
            openai_service=openai,
            redis_service=redis,
        )

        redis.get_session.assert_called_once_with("conv-123")
        # History should be passed to both classify and generate
        openai.classify_intent.assert_called_once_with(
            "What about for part-time employees?", prior_messages
        )

    @pytest.mark.asyncio
    async def test_no_conversation_id_skips_history(self) -> None:
        """UT-RAG-004b: Without conversation_id, history is empty."""
        search = AsyncMock()
        search.hybrid_search.return_value = [{"content": "text"}]

        openai = AsyncMock()
        openai.classify_intent.return_value = {
            "type": "factual",
            "domain": "HR",
            "confidence": 0.85,
        }
        openai.generate_answer.return_value = {
            "content": "Answer",
            "citations": [],
            "response_type": "answer",
        }

        redis = AsyncMock()

        await orchestrate_chat(
            message="What is the PTO policy?",
            conversation_id=None,
            user_id="user-1",
            user_email="user@acme.com",
            search_service=search,
            openai_service=openai,
            redis_service=redis,
        )

        redis.get_session.assert_not_called()
        openai.classify_intent.assert_called_once_with("What is the PTO policy?", [])


# ---------------------------------------------------------------------------
# UT-RAG-005: No-match path (FR-014, FR-027)
# ---------------------------------------------------------------------------


class TestOrchestrateChatNoMatch:
    """orchestrate_chat returns no_match when no policy content found."""

    @pytest.mark.asyncio
    async def test_no_match_when_no_chunks_and_low_confidence(self) -> None:
        """UT-RAG-005a: Empty search results + low confidence → no_match."""
        search = AsyncMock()
        search.hybrid_search.return_value = []

        openai = AsyncMock()
        openai.classify_intent.return_value = {
            "type": "unknown",
            "domain": None,
            "confidence": 0.23,
        }

        redis = AsyncMock()
        redis.get_session.return_value = None

        result = await orchestrate_chat(
            message="What is the policy on bringing dogs to the office?",
            conversation_id=None,
            user_id="user-1",
            user_email="user@acme.com",
            search_service=search,
            openai_service=openai,
            redis_service=redis,
        )

        assert result["response_type"] == "no_match"
        assert "suggested_escalation" in result
        assert result["suggested_escalation"]["team"] == "HR Service Desk"
        openai.generate_answer.assert_not_called()


# ---------------------------------------------------------------------------
# UT-RAG-006: Fallback on OpenAI failure (NFR-006)
# ---------------------------------------------------------------------------


class TestOrchestrateChatFallback:
    """orchestrate_chat returns fallback_search when OpenAI fails."""

    @pytest.mark.asyncio
    async def test_fallback_when_openai_raises(self) -> None:
        """UT-RAG-006: OpenAI exception → fallback with basic search results."""
        search = AsyncMock()
        search.hybrid_search.return_value = [
            {
                "document_title": "HR-POL-042",
                "section_heading": "Section 3.1",
                "content": "Bereavement leave provides up to 5 days of paid leave for...",
                "source_url": "https://intranet.acme.com/policies/HR-POL-042",
            }
        ]

        openai = AsyncMock()
        openai.classify_intent.return_value = {
            "type": "factual",
            "domain": "HR",
            "confidence": 0.85,
        }
        openai.generate_answer.side_effect = RuntimeError("Azure OpenAI unavailable")

        redis = AsyncMock()
        redis.get_session.return_value = None

        result = await orchestrate_chat(
            message="What is the bereavement leave policy?",
            conversation_id=None,
            user_id="user-1",
            user_email="user@acme.com",
            search_service=search,
            openai_service=openai,
            redis_service=redis,
        )

        assert result["response_type"] == "fallback_search"
        assert "search_results" in result
        assert len(result["search_results"]) == 1
        assert result["search_results"][0]["document_title"] == "HR-POL-042"


# ---------------------------------------------------------------------------
# UT-RAG-007: DISCLAIMER constant (FR-015)
# ---------------------------------------------------------------------------


class TestDisclaimer:
    """The DISCLAIMER constant matches the required text from FR-015."""

    def test_disclaimer_contains_required_text(self) -> None:
        """UT-RAG-007: Disclaimer text matches FR-015 requirement."""
        assert "not legal advice" in DISCLAIMER
        assert "verify the source document" in DISCLAIMER
