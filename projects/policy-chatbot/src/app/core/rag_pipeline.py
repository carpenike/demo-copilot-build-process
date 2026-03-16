"""RAG pipeline orchestration — search, prompt, generate, parse (ADR-0010)."""

import hashlib
import json
import logging
import time

from app.core.intent_classifier import (
    ClassificationResult,
    IntentResult,
    classify_intent,
)
from app.services.openai_service import DISCLAIMER, ChatResponse, OpenAIService
from app.services.redis_service import RedisService
from app.services.search_service import SearchResult, SearchService

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Orchestrates the full RAG pipeline from user query to grounded response."""

    def __init__(
        self,
        search_service: SearchService,
        openai_service: OpenAIService,
        redis_service: RedisService,
        *,
        top_k: int = 5,
        confidence_threshold: float = 0.6,
        max_conversation_history: int = 10,
    ) -> None:
        self._search = search_service
        self._openai = openai_service
        self._redis = redis_service
        self._top_k = top_k
        self._confidence_threshold = confidence_threshold
        self._max_history = max_conversation_history

    async def process_query(
        self,
        conversation_id: str,
        user_query: str,
    ) -> dict:  # type: ignore[type-arg]
        """Run the full RAG pipeline for a user query.

        Steps (per architecture-overview.md §4):
        1. Classify intent (confidential topic detection)
        2. Check response cache
        3. Generate query embedding
        4. Execute hybrid search
        5. Assemble prompt with conversation history
        6. Generate LLM response
        7. Parse and return structured output
        """
        start_time = time.monotonic()

        # Step 1: Intent classification (FR-008, FR-016)
        classification = classify_intent(user_query)

        if classification.intent == IntentResult.CONFIDENTIAL:
            return self._confidential_response()

        if classification.intent == IntentResult.ESCALATION_REQUEST:
            return self._escalation_request_response()

        # Step 2: Check response cache
        query_hash = hashlib.sha256(user_query.lower().strip().encode()).hexdigest()
        cached = await self._redis.get_cached_response(query_hash)
        if cached:
            logger.info("Cache hit for query", extra={"query_hash": query_hash})
            return json.loads(cached)

        # Step 3–7: Check LLM availability and branch accordingly
        llm_available = await self._openai.is_available()

        if llm_available:
            result = await self._rag_with_llm(
                conversation_id, user_query, classification, query_hash
            )
        else:
            result = await self._keyword_fallback(user_query)

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        result["response_time_ms"] = elapsed_ms

        return result

    async def _rag_with_llm(
        self,
        conversation_id: str,
        user_query: str,
        classification: ClassificationResult,
        query_hash: str,
    ) -> dict:  # type: ignore[type-arg]
        """Full RAG pipeline with LLM — normal operation mode."""
        # Step 3: Generate query embedding
        query_vector = await self._openai.generate_embedding(user_query)

        # Step 4: Hybrid search
        search_results = await self._search.hybrid_search(
            query_text=user_query,
            query_vector=query_vector,
            top_k=self._top_k,
        )

        if not search_results:
            return self._no_match_response()

        # Step 5: Get conversation history from Redis
        history = await self._redis.get_conversation_history(
            conversation_id, max_messages=self._max_history
        )

        # Prepare context chunks for prompt
        context_chunks = [
            {
                "document_title": r.document_title,
                "section_heading": r.section_heading or "",
                "effective_date": r.effective_date or "",
                "source_url": r.source_url or "",
                "content": r.content,
            }
            for r in search_results
        ]

        # Step 6: LLM chat completion
        chat_response = await self._openai.chat_completion(
            user_query=user_query,
            context_chunks=context_chunks,
            conversation_history=history,
        )

        # Step 7: Build structured response
        if chat_response.is_no_match:
            return self._no_match_response()

        result = self._build_response(chat_response, classification)

        # Cache the response
        await self._redis.set_cached_response(query_hash, json.dumps(result))

        return result

    async def _keyword_fallback(
        self,
        user_query: str,
    ) -> dict:  # type: ignore[type-arg]
        """Keyword-only search fallback when Azure OpenAI is unavailable (NFR-006)."""
        search_results = await self._search.keyword_search(
            query_text=user_query,
            top_k=self._top_k,
        )

        return {
            "response_type": "fallback_search",
            "content": (
                "I found some potentially relevant policy documents, but I'm "
                "currently operating in basic search mode. Here are the top results:"
            ),
            "search_results": [
                {
                    "document_title": r.document_title,
                    "section": r.section_heading or "",
                    "snippet": r.content[:300],
                    "source_url": r.source_url or "",
                }
                for r in search_results
            ],
            "fallback_notice": (
                "This is a basic search result, not a full answer. "
                "Try again later for a complete answer, or I can connect "
                "you with a support agent."
            ),
            "escalation_offered": True,
        }

    def _build_response(
        self,
        chat_response: ChatResponse,
        classification: ClassificationResult,
    ) -> dict:  # type: ignore[type-arg]
        """Assemble the final API response from parsed LLM output."""
        result: dict = {  # type: ignore[type-arg]
            "content": chat_response.content,
            "response_type": chat_response.response_type,
            "citations": chat_response.citations,
            "disclaimer": DISCLAIMER,
            "feedback_enabled": True,
            "intent": classification.intent.value,
            "query_type": classification.query_type.value,
        }

        if chat_response.checklist:
            result["checklist"] = chat_response.checklist

        return result

    def _no_match_response(self) -> dict:  # type: ignore[type-arg]
        """Standard response when no relevant policy is found (FR-014)."""
        return {
            "content": (
                "I wasn't able to find a policy covering that topic. "
                "Would you like me to connect you with HR support?"
            ),
            "response_type": "no_match",
            "citations": [],
            "disclaimer": DISCLAIMER,
            "escalation_offered": True,
            "feedback_enabled": True,
        }

    def _confidential_response(self) -> dict:  # type: ignore[type-arg]
        """Response for confidential HR matters — no AI answer generated (FR-016)."""
        return {
            "content": (
                "It sounds like your question may involve a sensitive HR matter. "
                "I want to make sure you get the right support. Would you like me "
                "to connect you directly with an HR representative who can help "
                "confidentially?"
            ),
            "response_type": "confidential_escalation",
            "escalation_offered": True,
            "feedback_enabled": False,
        }

    def _escalation_request_response(self) -> dict:  # type: ignore[type-arg]
        """Response when the user explicitly asks for a human agent (FR-025)."""
        return {
            "content": (
                "I'd be happy to connect you with a support agent. "
                "Which team would you like to speak with — HR, IT, or Facilities?"
            ),
            "response_type": "escalation_prompt",
            "escalation_offered": True,
            "feedback_enabled": False,
        }
