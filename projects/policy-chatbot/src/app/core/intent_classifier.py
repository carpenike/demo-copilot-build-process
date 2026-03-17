"""Intent classifier using GPT-4o-mini for query routing.

Classifies employee queries into policy domain, query type (factual,
procedural, sensitive), and detects confidential HR matters that must
be escalated without an AI-generated answer (FR-008, FR-016).
"""

from __future__ import annotations

import structlog

from app.services.llm_service import LLMService

logger = structlog.get_logger()

SENSITIVE_DOMAINS = frozenset(
    {
        "harassment",
        "discrimination",
        "whistleblower",
        "ethics",
        "retaliation",
        "complaint",
    }
)


class IntentResult:
    """Structured result from intent classification."""

    def __init__(
        self,
        domain: str | None,
        intent_type: str,
        is_sensitive: bool,
    ) -> None:
        self.domain = domain
        self.intent_type = intent_type
        self.is_sensitive = is_sensitive


async def classify_intent(
    llm_service: LLMService,
    query: str,
    conversation_context: list[dict[str, str]] | None = None,
) -> IntentResult:
    """Classify the user's intent using the LLM classifier.

    Detects sensitive topics (harassment, discrimination, whistleblower)
    and routes them to immediate escalation without generating an answer.
    """
    result = await llm_service.classify_intent(query, conversation_context)

    intent_type = result.get("type", "factual")
    domain = result.get("domain")
    is_sensitive = intent_type == "sensitive"

    if not is_sensitive:
        query_lower = query.lower()
        is_sensitive = any(keyword in query_lower for keyword in SENSITIVE_DOMAINS)
        if is_sensitive:
            intent_type = "sensitive"

    logger.info(
        "intent_classification_result",
        domain=domain,
        intent_type=intent_type,
        is_sensitive=is_sensitive,
    )

    return IntentResult(
        domain=domain,
        intent_type=intent_type,
        is_sensitive=is_sensitive,
    )
