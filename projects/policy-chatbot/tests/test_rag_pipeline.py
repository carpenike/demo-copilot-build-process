"""Unit tests for the RAG pipeline (FR-012–FR-015, FR-017, FR-027, NFR-006).

Tests are derived from requirements, not implementation:
- FR-012: RAG retrieves policy chunks and generates grounded answer
- FR-013: Every response includes citations
- FR-014: No answer when no relevant policy found
- FR-015: Standard disclaimer on every response
- FR-017: Procedural queries generate checklists
- FR-027: Auto-escalation after consecutive low-confidence answers
- NFR-006: Keyword fallback when LLM is unavailable
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.rag_pipeline import run_pipeline
from app.services.llm_service import DISCLAIMER


@pytest.fixture()
def mock_llm() -> AsyncMock:
    """LLM service mock for RAG pipeline tests."""
    service = AsyncMock()
    service.classify_intent = AsyncMock(
        return_value={"domain": "HR", "type": "factual", "reasoning": "test"}
    )
    service.generate_embedding = AsyncMock(return_value=[0.1] * 3072)
    service.generate_answer = AsyncMock(
        return_value={
            "answer": "Bereavement leave is 5 days for immediate family.",
            "citations": [
                {
                    "document_title": "Bereavement Leave Policy",
                    "section": "Section 3.2",
                    "effective_date": "2025-06-01",
                    "source_url": "https://intranet.acme.com/hr/bereavement",
                }
            ],
            "checklist": None,
            "confidence": 0.92,
        }
    )
    return service


@pytest.fixture()
def mock_search() -> AsyncMock:
    """Search service mock for RAG pipeline tests."""
    service = AsyncMock()
    service.hybrid_search = AsyncMock(
        return_value=[
            {
                "chunk_id": "chunk-1",
                "document_id": "doc-1",
                "content": "Bereavement leave is 5 days for immediate family.",
                "title": "Bereavement Leave Policy",
                "section_heading": "Section 3.2",
                "category": "HR",
                "effective_date": "2025-06-01",
                "source_url": "https://intranet.acme.com/hr/bereavement",
                "page_number": 3,
                "score": 0.95,
                "reranker_score": 0.88,
            }
        ]
    )
    service.keyword_search = AsyncMock(
        return_value=[
            {
                "chunk_id": "chunk-1",
                "document_id": "doc-1",
                "content": "Bereavement leave is 5 days.",
                "title": "Bereavement Leave Policy",
                "section_heading": "Section 3.2",
                "source_url": "https://intranet.acme.com/hr/bereavement",
            }
        ]
    )
    return service


class TestRAGPipelineHappyPath:
    """FR-012: RAG pipeline retrieves and generates grounded answers."""

    async def test_factual_query_returns_cited_answer(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """UT-005: Pipeline returns answer with citations for factual query."""
        result = await run_pipeline(
            query="What is the bereavement leave policy?",
            llm_service=mock_llm,
            search_service=mock_search,
        )

        assert result.response_body.content != ""
        assert result.response_body.confidence == 0.92
        assert result.should_escalate is False

    async def test_response_includes_citations(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """UT-006 / FR-013: Response includes citation block."""
        result = await run_pipeline(
            query="What is the bereavement leave policy?",
            llm_service=mock_llm,
            search_service=mock_search,
        )

        assert len(result.response_body.citations) == 1
        citation = result.response_body.citations[0]
        assert citation.document_title == "Bereavement Leave Policy"
        assert citation.section == "Section 3.2"
        assert citation.effective_date == "2025-06-01"
        assert citation.source_url != ""

    async def test_disclaimer_appended(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """UT-008 / FR-015: Standard disclaimer on every response."""
        result = await run_pipeline(
            query="What is the PTO policy?",
            llm_service=mock_llm,
            search_service=mock_search,
        )

        assert result.response_body.disclaimer == DISCLAIMER

    async def test_intent_info_included(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """FR-008: Intent info included in response."""
        result = await run_pipeline(
            query="What is the dress code?",
            llm_service=mock_llm,
            search_service=mock_search,
        )

        assert result.response_body.intent.domain == "HR"
        assert result.response_body.intent.type == "factual"


class TestRAGPipelineNoResults:
    """FR-014: No answer when no relevant policy found."""

    async def test_no_policy_found_response(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """UT-007: No relevant policy → offer to connect with support."""
        mock_search.hybrid_search = AsyncMock(return_value=[])

        result = await run_pipeline(
            query="Can I bring my dog to work?",
            llm_service=mock_llm,
            search_service=mock_search,
        )

        assert "wasn't able to find" in result.response_body.content.lower()
        assert result.response_body.citations == []
        assert result.response_body.confidence == 0.0
        assert result.should_escalate is True

    async def test_no_policy_found_still_has_disclaimer(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """FR-015: Disclaimer present even when no policy found."""
        mock_search.hybrid_search = AsyncMock(return_value=[])

        result = await run_pipeline(
            query="Unknown topic question",
            llm_service=mock_llm,
            search_service=mock_search,
        )

        assert result.response_body.disclaimer == DISCLAIMER


class TestRAGPipelineSensitiveTopic:
    """FR-016: Sensitive topics trigger immediate escalation."""

    async def test_sensitive_topic_escalates_immediately(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """UT-009: Sensitive query → escalation without AI answer."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": "HR", "type": "sensitive", "reasoning": "harassment"}
        )

        result = await run_pipeline(
            query="I want to report harassment",
            llm_service=mock_llm,
            search_service=mock_search,
        )

        assert result.response_body.escalated is True
        assert result.should_escalate is True
        assert result.escalation_reason == "sensitive_topic"
        assert "sensitive matter" in result.response_body.content.lower()
        # No citations should be provided for sensitive topics
        assert result.response_body.citations == []
        # No disclaimer for immediate escalation
        assert result.response_body.disclaimer is None

    async def test_sensitive_topic_does_not_call_search(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """FR-016: Search is NOT called for sensitive topics."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": "HR", "type": "sensitive", "reasoning": "test"}
        )

        await run_pipeline(
            query="discrimination complaint",
            llm_service=mock_llm,
            search_service=mock_search,
        )

        mock_search.hybrid_search.assert_not_called()
        mock_llm.generate_answer.assert_not_called()


class TestRAGPipelineChecklist:
    """FR-017: Procedural queries generate numbered checklists."""

    async def test_procedural_query_produces_checklist(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """UT-011: Procedural query returns checklist."""
        mock_llm.classify_intent = AsyncMock(
            return_value={"domain": "HR", "type": "procedural", "reasoning": "how-to"}
        )
        mock_llm.generate_answer = AsyncMock(
            return_value={
                "answer": "Here's how to request FMLA leave:",
                "citations": [
                    {
                        "document_title": "FMLA Policy",
                        "section": "Section 5",
                        "effective_date": "2025-01-15",
                        "source_url": "https://intranet.acme.com/hr/fmla",
                    }
                ],
                "checklist": {
                    "steps": [
                        {
                            "step_number": 1,
                            "text": "Notify your manager",
                            "type": "manual",
                            "details": "At least 30 days notice",
                        },
                        {
                            "step_number": 2,
                            "text": "Submit the form in Workday",
                            "type": "assisted",
                            "link": "https://workday.acme.com/fmla",
                            "link_label": "Open FMLA Form",
                        },
                    ]
                },
                "confidence": 0.88,
            }
        )

        result = await run_pipeline(
            query="How do I request FMLA leave?",
            llm_service=mock_llm,
            search_service=mock_search,
        )

        assert result.response_body.checklist is not None
        steps = result.response_body.checklist.steps
        assert len(steps) == 2
        assert steps[0].step_number == 1
        assert steps[0].type.value == "manual"
        assert steps[1].type.value == "assisted"
        assert steps[1].link is not None


class TestRAGPipelineLowConfidence:
    """FR-027: Auto-escalation after consecutive low-confidence answers."""

    async def test_low_confidence_triggers_should_escalate(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """UT-012: Low confidence sets should_escalate flag."""
        mock_llm.generate_answer = AsyncMock(
            return_value={
                "answer": "I'm not sure about this.",
                "citations": [],
                "checklist": None,
                "confidence": 0.3,
            }
        )

        result = await run_pipeline(
            query="Some unclear question",
            llm_service=mock_llm,
            search_service=mock_search,
            confidence_threshold=0.6,
        )

        assert result.should_escalate is True
        assert result.escalation_reason == "low_confidence"


class TestRAGPipelineFallback:
    """NFR-006: Keyword fallback when LLM is unavailable."""

    async def test_llm_failure_falls_back_to_keyword_search(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """UT-013: LLM failure triggers keyword fallback."""
        mock_llm.generate_embedding = AsyncMock(side_effect=Exception("LLM down"))

        result = await run_pipeline(
            query="What is the PTO policy?",
            llm_service=mock_llm,
            search_service=mock_search,
        )

        assert "basic search result" in result.response_body.content.lower()
        mock_search.keyword_search.assert_called_once()

    async def test_answer_generation_failure_falls_back(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """NFR-006: Answer generation failure also triggers fallback."""
        mock_llm.generate_answer = AsyncMock(side_effect=Exception("LLM down"))

        result = await run_pipeline(
            query="What is the PTO policy?",
            llm_service=mock_llm,
            search_service=mock_search,
        )

        assert "basic search result" in result.response_body.content.lower()

    async def test_complete_failure_returns_error_message(
        self, mock_llm: AsyncMock, mock_search: AsyncMock
    ) -> None:
        """NFR-006: Total failure returns a graceful error message."""
        mock_llm.generate_embedding = AsyncMock(side_effect=Exception("LLM down"))
        mock_search.keyword_search = AsyncMock(side_effect=Exception("Search also down"))

        result = await run_pipeline(
            query="What is the PTO policy?",
            llm_service=mock_llm,
            search_service=mock_search,
        )

        assert "unable" in result.response_body.content.lower()
