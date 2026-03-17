"""Unit tests for service layer classes.

Tests the service methods directly with mocked Azure SDK dependencies.
These are the coverage gap — integration tests mock services at the API
boundary, but service internals need direct testing.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_service import DISCLAIMER, LLMService


class TestLLMService:
    """Tests for Azure OpenAI interactions."""

    def _make_service(self) -> LLMService:
        settings = MagicMock()
        settings.azure_openai_endpoint = "https://test.openai.azure.com"
        settings.azure_openai_api_version = "2024-12-01-preview"
        settings.azure_openai_chat_deployment = "gpt-4o"
        settings.azure_openai_classifier_deployment = "gpt-4o-mini"
        settings.azure_openai_embedding_deployment = "text-embedding-3-large"
        settings.azure_openai_embedding_dimensions = 3072
        return LLMService(settings)

    async def test_classify_intent_returns_parsed_json(self) -> None:
        """LLM service parses JSON response from classifier."""
        service = self._make_service()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {"domain": "HR", "type": "factual", "reasoning": "test"}
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        service._client = mock_client

        result = await service.classify_intent("What is the PTO policy?")

        assert result["domain"] == "HR"
        assert result["type"] == "factual"

    async def test_classify_intent_includes_context(self) -> None:
        """Context messages are included in the LLM call."""
        service = self._make_service()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"domain": "HR", "type": "factual"}'

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        service._client = mock_client

        context = [{"role": "user", "content": "prior question"}]
        await service.classify_intent("follow up", context)

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        # System prompt + context + user query
        assert len(messages) >= 3

    async def test_generate_answer_returns_structured_output(self) -> None:
        """Answer generation returns parsed JSON with answer, citations, confidence."""
        service = self._make_service()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "answer": "PTO is 20 days.",
            "citations": [{"document_title": "PTO Policy", "section": "S1",
                           "effective_date": "2025-01-01", "source_url": "http://x"}],
            "checklist": None,
            "confidence": 0.95,
        })

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        service._client = mock_client

        result = await service.generate_answer(
            query="What is PTO?",
            context_chunks=[{"title": "PTO", "content": "20 days", "section_heading": "",
                             "effective_date": "", "source_url": ""}],
        )

        assert result["answer"] == "PTO is 20 days."
        assert result["confidence"] == 0.95
        assert len(result["citations"]) == 1

    async def test_generate_embedding_returns_vector(self) -> None:
        """Embedding generation returns a float list."""
        service = self._make_service()

        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]

        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response
        service._client = mock_client

        result = await service.generate_embedding("test text")

        assert result == [0.1, 0.2, 0.3]

    async def test_check_health_returns_true_on_success(self) -> None:
        """Health check returns True when models list succeeds."""
        service = self._make_service()
        mock_client = MagicMock()
        mock_client.models.list.return_value = []
        service._client = mock_client

        result = await service.check_health()
        assert result is True

    async def test_check_health_returns_false_on_failure(self) -> None:
        """Health check returns False when models list fails."""
        service = self._make_service()
        mock_client = MagicMock()
        mock_client.models.list.side_effect = Exception("connection refused")
        service._client = mock_client

        result = await service.check_health()
        assert result is False

    def test_format_context_produces_readable_text(self) -> None:
        """Context formatter creates indexed document blocks."""
        service = self._make_service()
        chunks = [
            {"title": "Doc A", "section_heading": "S1", "effective_date": "2025-01-01",
             "source_url": "http://a", "content": "Content A"},
            {"title": "Doc B", "section_heading": "", "effective_date": "",
             "source_url": "", "content": "Content B"},
        ]

        result = service._format_context(chunks)

        assert "Document 1: Doc A" in result
        assert "Document 2: Doc B" in result
        assert "Content A" in result
        assert "Content B" in result

    def test_disclaimer_constant_exists(self) -> None:
        """DISCLAIMER constant is defined and non-empty."""
        assert len(DISCLAIMER) > 0
        assert "legal advice" in DISCLAIMER.lower()


class TestSearchService:
    """Tests for Azure AI Search interactions."""

    def _make_service(self) -> Any:
        from app.services.search_service import SearchService

        settings = MagicMock()
        settings.azure_search_endpoint = "https://test.search.windows.net"
        settings.azure_search_index_name = "policy-documents"
        settings.azure_openai_embedding_dimensions = 3072
        return SearchService(settings)

    async def test_hybrid_search_returns_chunks(self) -> None:
        """Hybrid search parses results into chunk dicts."""
        service = self._make_service()

        mock_results = [
            {
                "chunk_id": "c1",
                "document_id": "d1",
                "content": "Test content",
                "title": "Test Doc",
                "section_heading": "S1",
                "category": "HR",
                "effective_date": "2025-01-01",
                "source_url": "http://test",
                "page_number": 1,
                "@search.score": 0.95,
                "@search.reranker_score": 0.88,
            }
        ]

        mock_client = MagicMock()
        mock_client.search.return_value = mock_results
        service._search_client = mock_client

        results = await service.hybrid_search(
            query_text="test", query_vector=[0.1] * 3072, top_k=5
        )

        assert len(results) == 1
        assert results[0]["chunk_id"] == "c1"
        assert results[0]["score"] == 0.95

    async def test_keyword_search_returns_chunks(self) -> None:
        """Keyword fallback search returns simplified chunks."""
        service = self._make_service()

        mock_results = [
            {
                "chunk_id": "c1",
                "document_id": "d1",
                "content": "Test",
                "title": "Doc",
                "section_heading": "S1",
                "source_url": "http://test",
            }
        ]

        mock_client = MagicMock()
        mock_client.search.return_value = mock_results
        service._search_client = mock_client

        results = await service.keyword_search("test", top_k=5)

        assert len(results) == 1
        assert results[0]["chunk_id"] == "c1"

    async def test_check_health_returns_true(self) -> None:
        """Health check returns True when index list succeeds."""
        service = self._make_service()
        mock_client = MagicMock()
        mock_client.list_indexes.return_value = []
        service._index_client = mock_client

        result = await service.check_health()
        assert result is True

    async def test_check_health_returns_false_on_failure(self) -> None:
        """Health check returns False on error."""
        service = self._make_service()
        mock_client = MagicMock()
        mock_client.list_indexes.side_effect = Exception("down")
        service._index_client = mock_client

        result = await service.check_health()
        assert result is False

    def test_generate_chunk_id_is_unique(self) -> None:
        """Chunk IDs include document ID and are unique."""
        service = self._make_service()
        id1 = service.generate_chunk_id("doc-1", 0)
        id2 = service.generate_chunk_id("doc-1", 1)
        assert id1 != id2
        assert "doc-1" in id1

    async def test_upsert_chunks_calls_upload(self) -> None:
        """Upsert delegates to the search client."""
        service = self._make_service()
        mock_client = MagicMock()
        service._search_client = mock_client

        await service.upsert_chunks([{"chunk_id": "c1", "content": "test"}])

        mock_client.upload_documents.assert_called_once()

    async def test_delete_document_chunks(self) -> None:
        """Delete removes chunks by document_id filter."""
        service = self._make_service()
        mock_client = MagicMock()
        mock_client.search.return_value = [{"chunk_id": "c1"}, {"chunk_id": "c2"}]
        service._search_client = mock_client

        await service.delete_document_chunks("doc-1")

        mock_client.delete_documents.assert_called_once()


class TestConversationService:
    """Tests for conversation context management."""

    def _make_service(self) -> Any:
        from app.services.conversation_service import ConversationService

        settings = MagicMock()
        settings.redis_session_ttl_seconds = 1800
        redis = AsyncMock()
        return ConversationService(settings, redis), redis

    async def test_get_conversation_context_empty(self) -> None:
        """Empty Redis returns empty context list."""
        service, redis = self._make_service()
        redis.get.return_value = None

        result = await service.get_conversation_context(uuid.uuid4())

        assert result == []

    async def test_get_conversation_context_with_data(self) -> None:
        """Cached context is returned as parsed JSON."""
        service, redis = self._make_service()
        redis.get.return_value = json.dumps([
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ])

        result = await service.get_conversation_context(uuid.uuid4())

        assert len(result) == 2
        assert result[0]["role"] == "user"

    async def test_update_conversation_context_stores_in_redis(self) -> None:
        """Context update appends and stores in Redis with TTL."""
        service, redis = self._make_service()
        redis.get.return_value = None

        conv_id = uuid.uuid4()
        await service.update_conversation_context(conv_id, "user", "hello")

        redis.set.assert_called_once()
        call_args = redis.set.call_args
        stored = json.loads(call_args.args[1])
        assert len(stored) == 1
        assert stored[0]["content"] == "hello"

    async def test_context_window_limited_to_10(self) -> None:
        """Context is trimmed to last 10 messages."""
        service, redis = self._make_service()
        existing = [{"role": "user", "content": f"msg-{i}"} for i in range(10)]
        redis.get.return_value = json.dumps(existing)

        await service.update_conversation_context(uuid.uuid4(), "user", "new")

        call_args = redis.set.call_args
        stored = json.loads(call_args.args[1])
        assert len(stored) == 10
        assert stored[-1]["content"] == "new"

    async def test_increment_low_confidence_count(self) -> None:
        """Low confidence counter is incremented in Redis."""
        service, redis = self._make_service()
        redis.incr.return_value = 2

        result = await service.increment_low_confidence_count(uuid.uuid4())

        assert result == 2
        redis.incr.assert_called_once()

    async def test_reset_low_confidence_count(self) -> None:
        """Low confidence counter is deleted from Redis."""
        service, redis = self._make_service()

        await service.reset_low_confidence_count(uuid.uuid4())

        redis.delete.assert_called_once()
