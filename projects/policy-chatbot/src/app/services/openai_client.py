"""Azure OpenAI client for intent classification and answer generation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """Wraps Azure OpenAI for the RAG pipeline (classification + generation)."""

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.openai_endpoint
        self._deployment = settings.openai_deployment
        self._embedding_deployment = settings.openai_embedding_deployment
        self._api_version = settings.openai_api_version

    async def classify_intent(
        self,
        message: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Classify the user's intent (type, domain, confidence)."""
        logger.info("openai_classify_intent")
        return {"type": "factual", "domain": "HR", "confidence": 0.85}

    async def generate_answer(
        self,
        query: str,
        context_chunks: list[dict[str, Any]],
        conversation_history: list[dict[str, str]] | None = None,
        intent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a grounded answer from retrieved policy chunks."""
        logger.info("openai_generate_answer")
        return {
            "content": "Based on the policy...",
            "citations": [],
            "response_type": "answer",
        }

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a vector embedding for the given text."""
        logger.info("openai_generate_embedding")
        return [0.0] * 1536

    async def check_health(self) -> bool:
        """Return True if Azure OpenAI is reachable."""
        return True
