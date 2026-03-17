"""Pydantic schemas for API request/response models.

These models match the wireframe spec in
projects/policy-chatbot/design/wireframe-spec.md.
"""

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# --- Enums ---


class IntentType(StrEnum):
    """Query intent classification types."""

    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    SENSITIVE = "sensitive"


class ChecklistStepType(StrEnum):
    """Whether the system can assist with a checklist step."""

    ASSISTED = "assisted"
    MANUAL = "manual"


class FeedbackRating(StrEnum):
    """Allowed feedback rating values."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class DocumentStatus(StrEnum):
    """Document lifecycle status."""

    PROCESSING = "processing"
    ACTIVE = "active"
    RETIRED = "retired"


# --- Chat API Schemas ---


class ChatRequest(BaseModel):
    """Request body for POST /api/v1/chat."""

    conversation_id: uuid.UUID | None = None
    message: str = Field(min_length=1, max_length=2000)


class Citation(BaseModel):
    """A reference to a source policy document."""

    document_title: str
    section: str
    effective_date: str
    source_url: str


class ContactInfo(BaseModel):
    """Contact details for an assisted checklist step."""

    name: str
    email: str
    phone: str
    office: str


class WayfindingInfo(BaseModel):
    """Location details for an assisted checklist step."""

    building: str
    room: str
    floor: int
    campus_map_url: str | None = None


class ChecklistStep(BaseModel):
    """A single step in a procedural checklist."""

    step_number: int
    text: str
    type: ChecklistStepType
    details: str | None = None
    link: str | None = None
    link_label: str | None = None
    contact: ContactInfo | None = None
    wayfinding: WayfindingInfo | None = None


class Checklist(BaseModel):
    """A procedural checklist derived from policy."""

    steps: list[ChecklistStep]


class IntentInfo(BaseModel):
    """Classified intent for a user query."""

    domain: str | None = None
    type: IntentType


class EscalationInfo(BaseModel):
    """Details of an escalation to a live agent."""

    reason: str
    servicenow_incident_id: str


class ChatResponseBody(BaseModel):
    """The chatbot's response content."""

    content: str
    citations: list[Citation] = Field(default_factory=list)
    checklist: Checklist | None = None
    disclaimer: str | None = (
        "This information is based on current corporate policy and is not legal advice. "
        "Policy details may have changed — verify the source document for the most current version."
    )
    intent: IntentInfo
    confidence: float | None = None
    escalated: bool = False
    escalation: EscalationInfo | None = None


class ChatResponse(BaseModel):
    """Response for POST /api/v1/chat."""

    conversation_id: uuid.UUID
    message_id: uuid.UUID
    response: ChatResponseBody


# --- Escalation ---


class EscalateRequest(BaseModel):
    """Request body for POST /api/v1/chat/{conversation_id}/escalate."""

    reason: str | None = None


class EscalationResponse(BaseModel):
    """Response for explicit escalation."""

    conversation_id: uuid.UUID
    escalation: EscalationInfo


# --- Feedback ---


class FeedbackRequest(BaseModel):
    """Request body for POST /api/v1/chat/{conversation_id}/feedback."""

    message_id: uuid.UUID
    rating: FeedbackRating
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    """Response for feedback submission."""

    feedback_id: uuid.UUID
    message_id: uuid.UUID
    rating: FeedbackRating
    comment: str | None = None


# --- Health ---


class HealthResponse(BaseModel):
    """Response for GET /health."""

    status: str


class ReadinessChecks(BaseModel):
    """Individual dependency check results."""

    database: str
    redis: str
    azure_openai: str
    ai_search: str


class ReadinessResponse(BaseModel):
    """Response for GET /ready."""

    status: str
    checks: ReadinessChecks


# --- Admin: Documents ---


class DocumentResponse(BaseModel):
    """A policy document in API responses."""

    id: uuid.UUID
    title: str
    document_external_id: str
    category: str
    effective_date: date
    review_date: date | None = None
    owner: str
    source_url: str | None = None
    status: DocumentStatus
    current_version: int
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    data: list[DocumentResponse]
    next_cursor: str | None = None
    total: int


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""

    id: uuid.UUID
    title: str
    status: DocumentStatus
    version: int
    message: str


class DocumentRetireResponse(BaseModel):
    """Response after retiring a document."""

    id: uuid.UUID
    title: str
    status: DocumentStatus
    message: str


class ReindexResponse(BaseModel):
    """Response after triggering re-indexing."""

    id: uuid.UUID | None = None
    status: str
    total_documents: int | None = None
    message: str


class ReindexStatusResponse(BaseModel):
    """Response for checking re-index progress."""

    status: str
    documents_processed: int
    documents_total: int
    started_at: datetime
    estimated_completion: datetime | None = None


class VersionInfo(BaseModel):
    """A single document version record."""

    version_number: int
    status: str
    indexed_by: str
    indexed_at: datetime | None = None
    created_at: datetime


class DocumentVersionsResponse(BaseModel):
    """Version history for a document."""

    document_id: uuid.UUID
    versions: list[VersionInfo]


# --- Admin: Test Query ---


class TestQueryRequest(BaseModel):
    """Request body for POST /api/admin/test-query."""

    query: str = Field(min_length=1, max_length=2000)
    staged_document_id: uuid.UUID | None = None


class TestQueryResult(BaseModel):
    """A single test query result (live or staged)."""

    content: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float | None = None


class TestQueryResponse(BaseModel):
    """Response for test query endpoint."""

    live_response: TestQueryResult
    staged_response: TestQueryResult | None = None


# --- Admin: Coverage ---


class CategoryCoverage(BaseModel):
    """Coverage info for a policy category."""

    name: str
    document_count: int
    status: str


class CoverageResponse(BaseModel):
    """Policy domain coverage report."""

    categories: list[CategoryCoverage]
    total_documents: int
    gaps: list[str] = Field(default_factory=list)


# --- Admin: Analytics ---


class AnalyticsSummary(BaseModel):
    """Summary metrics for the analytics dashboard."""

    total_queries: int
    resolution_rate: float
    escalation_rate: float
    average_satisfaction: float
    unanswered_count: int


class TopIntent(BaseModel):
    """A frequently asked intent."""

    intent: str
    count: int


class VolumeByPeriod(BaseModel):
    """Query volume for a time period."""

    date: str
    count: int


class AnalyticsPeriod(BaseModel):
    """Time period for analytics query."""

    start_date: str
    end_date: str
    granularity: str


class AnalyticsResponse(BaseModel):
    """Response for analytics dashboard."""

    period: AnalyticsPeriod
    summary: AnalyticsSummary
    top_intents: list[TopIntent]
    volume_by_period: list[VolumeByPeriod]


class UnansweredQuery(BaseModel):
    """An unanswered query entry."""

    query: str
    attempted_domain: str | None = None
    count: int
    last_asked: datetime


class UnansweredQueriesResponse(BaseModel):
    """Paginated unanswered queries."""

    data: list[UnansweredQuery]
    next_cursor: str | None = None


class FlaggedTopic(BaseModel):
    """A topic flagged for review due to negative feedback."""

    topic: str
    negative_feedback_count: int
    sample_queries: list[str]
    sample_comments: list[str]


class FlaggedTopicsResponse(BaseModel):
    """Topics flagged for admin review."""

    flagged_topics: list[FlaggedTopic]


# --- RFC 7807 Problem Details ---


class ProblemDetail(BaseModel):
    """RFC 7807 error response format."""

    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None
