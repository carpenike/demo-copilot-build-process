"""RAG orchestration — intent classification, retrieval, and answer generation."""

from __future__ import annotations

import logging
from typing import Any

from app.services.openai_client import OpenAIService
from app.services.redis_client import RedisService
from app.services.search import SearchService

logger = logging.getLogger(__name__)

# Topics that trigger confidential escalation (FR-016)
CONFIDENTIAL_KEYWORDS = frozenset(
    {
        "harassment",
        "discrimination",
        "whistleblower",
        "retaliation",
        "sexual harassment",
        "hostile work environment",
    }
)

DISCLAIMER = (
    "This information is based on current corporate policy and is not legal advice. "
    "Policy details may have changed — verify the source document for the most current version."
)


async def detect_confidential_topic(message: str) -> bool:
    """Return True if the message relates to a confidential HR matter."""
    lower = message.lower()
    return any(kw in lower for kw in CONFIDENTIAL_KEYWORDS)


async def orchestrate_chat(
    *,
    message: str,
    conversation_id: str | None,
    user_id: str,
    user_email: str,
    search_service: SearchService,
    openai_service: OpenAIService,
    redis_service: RedisService,
) -> dict[str, Any]:
    """Run the full RAG pipeline: classify intent → retrieve → generate answer."""

    # 1. Check for confidential topic (FR-016)
    if await detect_confidential_topic(message):
        return {
            "response_type": "confidential_escalation",
            "content": (
                "This appears to be a sensitive matter that requires confidential support. "
                "I'm connecting you directly with HR rather than providing an automated response."
            ),
            "citations": [],
            "intent": None,
            "escalation": {
                "team": "HR Confidential Support",
                "phone": "+1-555-0199",
                "email": "confidential-hr@acme.com",
                "note": "All communications are handled confidentially.",
            },
        }

    # 2. Load conversation history from Redis for context (FR-009)
    history: list[dict[str, str]] = []
    if conversation_id:
        session = await redis_service.get_session(conversation_id)
        if session and "messages" in session:
            history = session["messages"]  # type: ignore[assignment]

    # 3. Classify intent (FR-008)
    intent = await openai_service.classify_intent(message, history)

    # 4. Retrieve relevant policy chunks (ADR-0010)
    chunks = await search_service.hybrid_search(
        message,
        top_k=5,
        category_filter=intent.get("domain"),
    )

    # 5. Handle no-match scenario (FR-014)
    if not chunks and intent.get("confidence", 0) < 0.5:
        return {
            "response_type": "no_match",
            "content": (
                "I couldn't find a matching policy for your question. "
                "Would you like me to connect you with the appropriate support team?"
            ),
            "citations": [],
            "intent": intent,
            "suggested_escalation": {
                "team": "HR Service Desk",
                "channel": "servicenow",
            },
        }

    # 6. Generate grounded answer (FR-012)
    try:
        result = await openai_service.generate_answer(
            query=message,
            context_chunks=chunks,
            conversation_history=history,
            intent=intent,
        )
    except Exception:
        logger.exception("openai_generation_failed")
        # Fallback to basic search results (NFR-006)
        return {
            "response_type": "fallback_search",
            "content": (
                "The AI assistant is temporarily unavailable. "
                "Here are basic search results that may help:"
            ),
            "citations": [],
            "intent": intent,
            "search_results": [
                {
                    "document_title": c.get("document_title", ""),
                    "section": c.get("section_heading", ""),
                    "snippet": c.get("content", "")[:200],
                    "source_url": c.get("source_url"),
                }
                for c in chunks[:3]
            ],
        }

    result["intent"] = intent
    result.setdefault("response_type", "answer")
    result.setdefault("citations", [])
    return result
