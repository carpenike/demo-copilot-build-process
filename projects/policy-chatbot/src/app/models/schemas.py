"""Pydantic request/response schemas — avoid class names starting with 'Test'."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str


class ReadyChecks(BaseModel):
    database: str
    redis: str
    search: str
    openai: str


class ReadyResponse(BaseModel):
    status: str
    checks: ReadyChecks


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str = Field(..., min_length=1, max_length=2000)


class CitationItem(BaseModel):
    document_title: str
    section: str
    effective_date: str | None = None
    source_url: str | None = None


class IntentInfo(BaseModel):
    type: str
    domain: str | None = None
    confidence: float


class ChecklistStep(BaseModel):
    step: int
    description: str
    action_type: str
    details: str | None = None
    assistance: dict[str, Any] | None = None


class WayfindingInfo(BaseModel):
    available: bool
    building: str | None = None
    floor: str | None = None
    room: str | None = None
    campus_map_url: str | None = None


class EscalationSuggestion(BaseModel):
    team: str
    channel: str | None = None
    phone: str | None = None
    email: str | None = None
    note: str | None = None


class SearchResultItem(BaseModel):
    document_title: str
    section: str
    snippet: str
    source_url: str | None = None


class ChatResponseBody(BaseModel):
    type: str
    content: str
    citations: list[CitationItem] = Field(default_factory=list)
    disclaimer: str = (
        "This information is based on current corporate policy and is not legal advice. "
        "Policy details may have changed — verify the source document for the most current version."
    )
    intent: IntentInfo | None = None
    checklist: list[ChecklistStep] | None = None
    wayfinding: WayfindingInfo | None = None
    suggested_escalation: EscalationSuggestion | None = None
    escalation: EscalationSuggestion | None = None
    search_results: list[SearchResultItem] | None = None


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    response: ChatResponseBody


# ---------------------------------------------------------------------------
# Escalation
# ---------------------------------------------------------------------------
class EscalateRequest(BaseModel):
    conversation_id: uuid.UUID


class EscalationResult(BaseModel):
    status: str
    ticket_id: str
    team: str
    message: str


class EscalateResponse(BaseModel):
    conversation_id: uuid.UUID
    escalation: EscalationResult


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------
class ConversationSummary(BaseModel):
    id: uuid.UUID
    started_at: datetime
    last_message_at: datetime | None = None
    message_count: int
    preview: str | None = None


class ConversationListResponse(BaseModel):
    data: list[ConversationSummary]
    next_cursor: str | None = None


class MessageItem(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    citations: list[CitationItem] | None = None
    timestamp: datetime


class ConversationDetailResponse(BaseModel):
    id: uuid.UUID
    started_at: datetime
    messages: list[MessageItem]


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
class FeedbackRequest(BaseModel):
    message_id: uuid.UUID
    rating: str = Field(..., pattern=r"^(positive|negative)$")
    comment: str | None = Field(None, max_length=500)


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    rating: str
    comment: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------
class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    department: str | None = None
    location: str | None = None
    role: str
    manager: str | None = None


# ---------------------------------------------------------------------------
# Admin — Documents
# ---------------------------------------------------------------------------
class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    category: str
    status: str
    effective_date: date
    review_date: date | None = None
    owner: str
    source_url: str | None = None
    current_version: int
    last_indexed_at: datetime | None = None
    page_count: int
    created_at: datetime | None = None


class DocumentVersionItem(BaseModel):
    version: int
    uploaded_at: datetime
    uploaded_by: str
    is_active: bool
    blob_path: str


class DocumentDetailResponse(DocumentResponse):
    versions: list[DocumentVersionItem] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    data: list[DocumentResponse]
    next_cursor: str | None = None


class DocumentCreateResponse(BaseModel):
    id: uuid.UUID
    title: str
    category: str
    status: str
    effective_date: date
    owner: str
    version: int
    indexing_status: str
    created_at: datetime


class DocumentUpdateResponse(BaseModel):
    id: uuid.UUID
    title: str
    version: int
    indexing_status: str
    updated_at: datetime


class DocumentPatchResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    updated_at: datetime


class ReindexDocumentResponse(BaseModel):
    document_id: uuid.UUID
    indexing_status: str
    estimated_completion: datetime | None = None


class ReindexCorpusResponse(BaseModel):
    indexing_status: str
    document_count: int
    estimated_completion: datetime | None = None


class DocumentPatchRequest(BaseModel):
    status: str | None = None
    title: str | None = None
    category: str | None = None
    effective_date: date | None = None
    review_date: date | None = None
    owner: str | None = None
    source_url: str | None = None


# ---------------------------------------------------------------------------
# Admin — Query Preview
# ---------------------------------------------------------------------------
class QueryPreviewRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    draft_document_id: uuid.UUID | None = None


class QueryPreviewAnswer(BaseModel):
    content: str
    citations: list[CitationItem] = Field(default_factory=list)
    intent: IntentInfo | None = None


class QueryPreviewResponse(BaseModel):
    live_answer: QueryPreviewAnswer
    preview_answer: QueryPreviewAnswer | None = None


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class DailyVolume(BaseModel):
    date: date
    count: int


class AnalyticsSummaryResponse(BaseModel):
    period: str
    total_queries: int
    resolution_rate: float
    escalation_rate: float
    average_satisfaction: float
    no_match_rate: float
    daily_volumes: list[DailyVolume] = Field(default_factory=list)


class IntentStat(BaseModel):
    intent: str
    domain: str
    count: int
    resolution_rate: float


class TopIntentsResponse(BaseModel):
    data: list[IntentStat]


class UnansweredItem(BaseModel):
    id: uuid.UUID
    query_text: str
    detected_intent: str | None = None
    detected_domain: str | None = None
    timestamp: datetime


class UnansweredResponse(BaseModel):
    data: list[UnansweredItem]
    next_cursor: str | None = None


class FlaggedTopicItem(BaseModel):
    topic: str
    domain: str
    negative_count: int
    sample_comments: list[str] = Field(default_factory=list)
    first_flagged_at: datetime


class FlaggedTopicsResponse(BaseModel):
    data: list[FlaggedTopicItem]
    next_cursor: str | None = None


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------
class CategoryCoverage(BaseModel):
    category: str
    document_count: int
    total_pages: int
    last_indexed_at: datetime | None = None
    status: str


class CoverageResponse(BaseModel):
    categories: list[CategoryCoverage]
    total_documents: int
    total_pages: int
    categories_with_gaps: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# RFC 7807 Problem Details
# ---------------------------------------------------------------------------
class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None
