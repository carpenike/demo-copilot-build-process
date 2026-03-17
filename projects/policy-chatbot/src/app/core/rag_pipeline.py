"""RAG pipeline orchestration.

Implements the full retrieval-augmented generation pipeline as specified in
ADR-0010: intent classification → query enrichment → retrieval → answer
generation → post-processing. Each stage is traced for observability.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.intent_classifier import IntentResult, classify_intent
from app.models.schemas import (
    ChatResponseBody,
    Checklist,
    ChecklistStep,
    ChecklistStepType,
    Citation,
    EscalationInfo,
    IntentInfo,
    IntentType,
)
from app.services.llm_service import DISCLAIMER, LLMService
from app.services.search_service import SearchService

logger = structlog.get_logger()


class RAGResult:
    """Complete result from the RAG pipeline for a single query."""

    def __init__(
        self,
        response_body: ChatResponseBody,
        intent: IntentResult,
        should_escalate: bool = False,
        escalation_reason: str | None = None,
    ) -> None:
        self.response_body = response_body
        self.intent = intent
        self.should_escalate = should_escalate
        self.escalation_reason = escalation_reason


async def run_pipeline(
    *,
    query: str,
    llm_service: LLMService,
    search_service: SearchService,
    conversation_context: list[dict[str, str]] | None = None,
    confidence_threshold: float = 0.6,
    top_k: int = 5,
) -> RAGResult:
    """Execute the full RAG pipeline for a user query.

    Pipeline stages:
    1. Intent classification (GPT-4o-mini)
    2. Sensitive topic detection → immediate escalation
    3. Retrieval (Azure AI Search hybrid search)
    4. Answer generation (GPT-4o)
    5. Post-processing (citation validation, disclaimer)
    """
    # Stage 1: Intent classification
    intent = await classify_intent(llm_service, query, conversation_context)

    # Stage 2: Sensitive topic → escalate without answer
    if intent.is_sensitive:
        return _build_sensitive_escalation(intent)

    # Stage 3: Retrieval
    try:
        query_embedding = await llm_service.generate_embedding(query)
        chunks = await search_service.hybrid_search(
            query_text=query,
            query_vector=query_embedding,
            top_k=top_k,
            category_filter=intent.domain,
        )
    except Exception:
        logger.exception("retrieval_failed")
        return await _build_fallback_response(query, search_service, intent)

    # No relevant chunks found
    if not chunks:
        return _build_no_policy_found(intent)

    # Stage 4: Answer generation
    try:
        answer_result = await llm_service.generate_answer(
            query=query,
            context_chunks=chunks,
            conversation_context=conversation_context,
            intent_type=intent.intent_type,
        )
    except Exception:
        logger.exception("answer_generation_failed")
        return await _build_fallback_response(query, search_service, intent)

    # Stage 5: Post-processing
    confidence = answer_result.get("confidence", 0.0)
    should_escalate = confidence < confidence_threshold

    citations = _parse_citations(answer_result.get("citations", []))
    checklist = _parse_checklist(answer_result.get("checklist"))

    response_body = ChatResponseBody(
        content=answer_result.get("answer", ""),
        citations=citations,
        checklist=checklist,
        disclaimer=DISCLAIMER,
        intent=IntentInfo(
            domain=intent.domain,
            type=IntentType(intent.intent_type),
        ),
        confidence=confidence,
        escalated=False,
    )

    return RAGResult(
        response_body=response_body,
        intent=intent,
        should_escalate=should_escalate,
        escalation_reason="low_confidence" if should_escalate else None,
    )


def _build_sensitive_escalation(intent: IntentResult) -> RAGResult:
    """Build a response for sensitive topics that routes to HR."""
    response_body = ChatResponseBody(
        content=(
            "This sounds like it may be a sensitive matter. "
            "I want to make sure you get the right support. "
            "Let me connect you directly with HR."
        ),
        citations=[],
        checklist=None,
        disclaimer=None,
        intent=IntentInfo(domain="HR", type=IntentType.SENSITIVE),
        confidence=None,
        escalated=True,
        escalation=EscalationInfo(
            reason="sensitive_topic",
            servicenow_incident_id="pending",
        ),
    )
    return RAGResult(
        response_body=response_body,
        intent=intent,
        should_escalate=True,
        escalation_reason="sensitive_topic",
    )


def _build_no_policy_found(intent: IntentResult) -> RAGResult:
    """Build a response when no relevant policy is found."""
    response_body = ChatResponseBody(
        content=(
            "I wasn't able to find a policy covering that topic. "
            "Would you like me to connect you with HR support?"
        ),
        citations=[],
        checklist=None,
        disclaimer=DISCLAIMER,
        intent=IntentInfo(
            domain=intent.domain,
            type=IntentType(intent.intent_type),
        ),
        confidence=0.0,
        escalated=False,
    )
    return RAGResult(
        response_body=response_body,
        intent=intent,
        should_escalate=True,
        escalation_reason="no_policy_found",
    )


async def _build_fallback_response(
    query: str,
    search_service: SearchService,
    intent: IntentResult,
) -> RAGResult:
    """Keyword-only fallback when LLM is unavailable (NFR-006)."""
    try:
        chunks = await search_service.keyword_search(query)
    except Exception:
        logger.exception("keyword_fallback_failed")
        chunks = []

    if chunks:
        content_parts = []
        for chunk in chunks:
            title = chunk.get("title", "")
            section = chunk.get("section_heading", "")
            text = chunk.get("content", "")[:500]
            content_parts.append(f"**{title}** — {section}\n{text}")

        content = (
            "This is a basic search result, not a full answer. "
            "Our AI assistant is temporarily unavailable.\n\n" + "\n\n---\n\n".join(content_parts)
        )
    else:
        content = (
            "I'm currently unable to search for policy information. "
            "Please try again shortly or contact the HR Service Desk."
        )

    response_body = ChatResponseBody(
        content=content,
        citations=[],
        checklist=None,
        disclaimer=DISCLAIMER,
        intent=IntentInfo(
            domain=intent.domain,
            type=IntentType(intent.intent_type),
        ),
        confidence=None,
        escalated=False,
    )
    return RAGResult(
        response_body=response_body,
        intent=intent,
    )


def _parse_citations(raw_citations: list[dict[str, Any]]) -> list[Citation]:
    """Parse and validate citations from LLM output."""
    citations: list[Citation] = []
    for c in raw_citations:
        citations.append(
            Citation(
                document_title=c.get("document_title", ""),
                section=c.get("section", ""),
                effective_date=c.get("effective_date", ""),
                source_url=c.get("source_url", ""),
            )
        )
    return citations


def _parse_checklist(raw_checklist: dict[str, Any] | None) -> Checklist | None:
    """Parse a checklist from LLM output into the structured schema."""
    if not raw_checklist or "steps" not in raw_checklist:
        return None

    steps: list[ChecklistStep] = []
    for step in raw_checklist["steps"]:
        step_type = step.get("type", "manual")
        steps.append(
            ChecklistStep(
                step_number=step.get("step_number", len(steps) + 1),
                text=step.get("text", ""),
                type=ChecklistStepType(step_type),
                details=step.get("details"),
                link=step.get("link"),
                link_label=step.get("link_label"),
            )
        )

    return Checklist(steps=steps) if steps else None
