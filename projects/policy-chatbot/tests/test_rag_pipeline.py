"""Unit tests for the RAG pipeline (FR-012, FR-013, FR-014, FR-015, FR-016, NFR-006).

Tests derived from requirements, NOT from implementation code.
All external services are mocked — no network calls in unit tests.
"""

import json
from unittest.mock import AsyncMock

import pytest

from app.core.rag_pipeline import RAGPipeline
from app.services.openai_service import DISCLAIMER, ChatResponse
from app.services.search_service import SearchResult


def _make_search_result(**overrides: object) -> SearchResult:
    """Create a SearchResult with sensible defaults."""
    defaults = {
        "document_id": "doc-001",
        "version_id": "ver-001",
        "chunk_index": 0,
        "content": "Employees are entitled to 20 days of PTO per year.",
        "section_heading": "§3.1 PTO Allowance",
        "document_title": "PTO Policy",
        "category": "HR",
        "effective_date": "2025-01-01",
        "source_url": "https://sharepoint.acme.com/policies/hr/pto",
        "score": 0.95,
    }
    defaults.update(overrides)
    return SearchResult(**defaults)  # type: ignore[arg-type]


def _make_chat_response(**overrides: object) -> ChatResponse:
    """Create a ChatResponse with sensible defaults."""
    defaults = {
        "content": "You are entitled to 20 days of PTO per year.",
        "response_type": "answer",
        "citations": [
            {
                "document_title": "PTO Policy",
                "section": "§3.1 PTO Allowance",
                "effective_date": "2025-01-01",
                "source_url": "https://sharepoint.acme.com/policies/hr/pto",
            }
        ],
        "checklist": None,
        "is_no_match": False,
    }
    defaults.update(overrides)
    return ChatResponse(**defaults)  # type: ignore[arg-type]


class TestRAGPipelineHappyPath:
    """FR-012, FR-013, FR-015: Normal RAG operation with grounded answer."""

    @pytest.mark.asyncio()
    async def test_returns_answer_with_citations(
        self,
        mock_search: AsyncMock,
        mock_openai: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        """UT-RAG-002, UT-RAG-003: RAG pipeline returns answer with citations."""
        mock_search.hybrid_search.return_value = [_make_search_result()]
        mock_openai.chat_completion.return_value = _make_chat_response()

        pipeline = RAGPipeline(mock_search, mock_openai, mock_redis)
        result = await pipeline.process_query("conv-1", "What is the PTO policy?")

        assert result["response_type"] == "answer"
        assert len(result["citations"]) > 0
        assert result["citations"][0]["document_title"] == "PTO Policy"

    @pytest.mark.asyncio()
    async def test_response_includes_disclaimer(
        self,
        mock_search: AsyncMock,
        mock_openai: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        """UT-RAG-005: Every response includes the standard disclaimer (FR-015)."""
        mock_search.hybrid_search.return_value = [_make_search_result()]
        mock_openai.chat_completion.return_value = _make_chat_response()

        pipeline = RAGPipeline(mock_search, mock_openai, mock_redis)
        result = await pipeline.process_query("conv-1", "What is the PTO policy?")

        assert "disclaimer" in result
        assert result["disclaimer"] == DISCLAIMER

    @pytest.mark.asyncio()
    async def test_conversation_history_is_loaded(
        self,
        mock_search: AsyncMock,
        mock_openai: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        """UT-RAG-001: Conversation history from Redis is passed to LLM (FR-009)."""
        mock_redis.get_conversation_history.return_value = [
            {"role": "user", "content": "What is the PTO policy?"},
            {"role": "assistant", "content": "You get 20 days."},
        ]
        mock_search.hybrid_search.return_value = [_make_search_result()]
        mock_openai.chat_completion.return_value = _make_chat_response()

        pipeline = RAGPipeline(mock_search, mock_openai, mock_redis)
        await pipeline.process_query("conv-1", "What about part-time employees?")

        # Verify conversation history was retrieved
        mock_redis.get_conversation_history.assert_called_once()
        # Verify LLM was called with history
        mock_openai.chat_completion.assert_called_once()

    @pytest.mark.asyncio()
    async def test_response_includes_timing(
        self,
        mock_search: AsyncMock,
        mock_openai: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        """Response includes response_time_ms for analytics tracking."""
        mock_search.hybrid_search.return_value = [_make_search_result()]
        mock_openai.chat_completion.return_value = _make_chat_response()

        pipeline = RAGPipeline(mock_search, mock_openai, mock_redis)
        result = await pipeline.process_query("conv-1", "PTO policy?")

        assert "response_time_ms" in result
        assert isinstance(result["response_time_ms"], int)


class TestRAGPipelineNoMatch:
    """FR-014: No relevant policy found."""

    @pytest.mark.asyncio()
    async def test_no_search_results_returns_no_match(
        self,
        mock_search: AsyncMock,
        mock_openai: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        """UT-RAG-004: Empty search results → no_match response."""
        mock_search.hybrid_search.return_value = []

        pipeline = RAGPipeline(mock_search, mock_openai, mock_redis)
        result = await pipeline.process_query("conv-1", "What about pet-friendly offices?")

        assert result["response_type"] == "no_match"
        assert "I wasn't able to find" in result["content"]
        assert result["escalation_offered"] is True

    @pytest.mark.asyncio()
    async def test_llm_says_no_relevant_policy(
        self,
        mock_search: AsyncMock,
        mock_openai: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        """UT-OAI-001: LLM returns NO_RELEVANT_POLICY token → no_match."""
        mock_search.hybrid_search.return_value = [_make_search_result()]
        mock_openai.chat_completion.return_value = _make_chat_response(
            is_no_match=True
        )

        pipeline = RAGPipeline(mock_search, mock_openai, mock_redis)
        result = await pipeline.process_query("conv-1", "random question")

        assert result["response_type"] == "no_match"


class TestRAGPipelineConfidential:
    """FR-016: Confidential topics bypass RAG entirely."""

    @pytest.mark.asyncio()
    async def test_confidential_query_bypasses_rag(
        self,
        mock_search: AsyncMock,
        mock_openai: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        """UT-RAG-006: Confidential query → no search, no LLM call."""
        pipeline = RAGPipeline(mock_search, mock_openai, mock_redis)
        result = await pipeline.process_query(
            "conv-1", "I want to report harassment"
        )

        assert result["response_type"] == "confidential_escalation"
        assert result["escalation_offered"] is True
        assert result["feedback_enabled"] is False
        # No search or LLM calls should have been made
        mock_search.hybrid_search.assert_not_called()
        mock_openai.chat_completion.assert_not_called()


class TestRAGPipelineEscalation:
    """FR-025: Explicit escalation requests."""

    @pytest.mark.asyncio()
    async def test_escalation_request_detected(
        self,
        mock_search: AsyncMock,
        mock_openai: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        pipeline = RAGPipeline(mock_search, mock_openai, mock_redis)
        result = await pipeline.process_query(
            "conv-1", "I want to talk to a person"
        )

        assert result["response_type"] == "escalation_prompt"
        assert result["escalation_offered"] is True
        mock_search.hybrid_search.assert_not_called()
        mock_openai.chat_completion.assert_not_called()


class TestRAGPipelineFallback:
    """NFR-006: Keyword fallback when LLM is unavailable."""

    @pytest.mark.asyncio()
    async def test_fallback_when_llm_unavailable(
        self,
        mock_search: AsyncMock,
        mock_openai: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        """UT-RAG-007: LLM unavailable → keyword search fallback."""
        mock_openai.is_available.return_value = False
        mock_search.keyword_search.return_value = [_make_search_result()]

        pipeline = RAGPipeline(mock_search, mock_openai, mock_redis)
        result = await pipeline.process_query("conv-1", "PTO policy?")

        assert result["response_type"] == "fallback_search"
        assert "basic search" in result["fallback_notice"]
        assert result["escalation_offered"] is True
        # Verify keyword search was used instead of hybrid
        mock_search.keyword_search.assert_called_once()
        mock_search.hybrid_search.assert_not_called()

    @pytest.mark.asyncio()
    async def test_fallback_snippets_are_truncated(
        self,
        mock_search: AsyncMock,
        mock_openai: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        """Fallback results include truncated snippets, not full content."""
        mock_openai.is_available.return_value = False
        long_content = "A" * 500
        mock_search.keyword_search.return_value = [
            _make_search_result(content=long_content)
        ]

        pipeline = RAGPipeline(mock_search, mock_openai, mock_redis)
        result = await pipeline.process_query("conv-1", "PTO policy?")

        for sr in result["search_results"]:
            assert len(sr["snippet"]) <= 300


class TestRAGPipelineCaching:
    """Response caching for identical queries."""

    @pytest.mark.asyncio()
    async def test_cached_response_returned(
        self,
        mock_search: AsyncMock,
        mock_openai: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        """Cached response is returned without calling search or LLM."""
        cached_data = {
            "content": "Cached answer",
            "response_type": "answer",
            "citations": [],
        }
        mock_redis.get_cached_response.return_value = json.dumps(cached_data)

        pipeline = RAGPipeline(mock_search, mock_openai, mock_redis)
        result = await pipeline.process_query("conv-1", "What is the PTO policy?")

        assert result["content"] == "Cached answer"
        mock_search.hybrid_search.assert_not_called()
        mock_openai.chat_completion.assert_not_called()

    @pytest.mark.asyncio()
    async def test_response_is_cached_after_generation(
        self,
        mock_search: AsyncMock,
        mock_openai: AsyncMock,
        mock_redis: AsyncMock,
    ) -> None:
        """After generating a response, it is stored in the cache."""
        mock_search.hybrid_search.return_value = [_make_search_result()]
        mock_openai.chat_completion.return_value = _make_chat_response()

        pipeline = RAGPipeline(mock_search, mock_openai, mock_redis)
        await pipeline.process_query("conv-1", "What is the PTO policy?")

        mock_redis.set_cached_response.assert_called_once()
