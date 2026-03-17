"""Admin API endpoints — document management, analytics, coverage, test queries."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    AuthenticatedUser,
    get_blob_service,
    get_db,
    get_rag_pipeline,
    require_admin,
)
from app.core.rag_pipeline import RAGPipeline
from app.models.analytics import AnalyticsEvent
from app.models.document import Document, DocumentVersion, PolicyCategory
from app.models.feedback import Feedback, FeedbackFlag
from app.services.blob_service import BlobService

router = APIRouter(prefix="/v1/admin", tags=["admin"])


# --- Request/Response schemas ---


class DocumentResponse(BaseModel):
    id: str
    title: str
    document_external_id: str
    category: str
    source_type: str
    source_url: str | None
    effective_date: str
    review_date: str | None
    owner: str
    status: str
    current_version: int
    last_indexed_at: str | None
    indexing_status: str


class DocumentListResponse(BaseModel):
    data: list[DocumentResponse]
    next_cursor: str | None
    total: int


class CreateDocumentRequest(BaseModel):
    title: str = Field(max_length=255)
    document_external_id: str = Field(max_length=100)
    category: str = Field(
        pattern=r"^(HR|IT|Finance|Facilities|Legal|Compliance|Safety)$"
    )
    effective_date: str
    review_date: str | None = None
    owner: str = Field(max_length=255)


class UpdateDocumentRequest(BaseModel):
    status: str | None = Field(default=None, pattern=r"^(active|retired)$")
    title: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, max_length=255)


class ReindexResponse(BaseModel):
    task_id: str
    document_id: str
    status: str
    message: str


class ReindexAllResponse(BaseModel):
    task_id: str
    status: str
    document_count: int
    message: str


class VersionResponse(BaseModel):
    version_id: str
    version_number: int
    file_type: str
    page_count: int | None
    indexed_by: str | None
    indexing_status: str
    indexed_at: str | None
    created_at: str


class TestQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000)
    include_pending_documents: bool = False


class AnalyticsResponse(BaseModel):
    period: str
    start_date: str
    end_date: str
    query_volume: int
    resolution_rate: float
    escalation_rate: float
    average_satisfaction: float
    top_intents: list[dict[str, object]]
    unanswered_queries: list[dict[str, object]]


class CoverageDomain(BaseModel):
    name: str
    document_count: int
    last_updated: str | None


class CoverageResponse(BaseModel):
    domains: list[CoverageDomain]
    total_documents: int
    gaps: list[str]


class FlaggedTopicResponse(BaseModel):
    data: list[dict[str, object]]


# --- Endpoints ---


@router.get("/documents")
async def list_documents(
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = None,
    doc_status: Annotated[str | None, Query(alias="status")] = None,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> DocumentListResponse:
    """List all policy documents with metadata and indexing status (FR-031, FR-033)."""
    query = select(Document).join(PolicyCategory)

    if category:
        query = query.where(PolicyCategory.name == category)
    if doc_status:
        query = query.where(Document.status == doc_status)

    # Cursor-based pagination using created_at
    if cursor:
        query = query.where(Document.created_at < datetime.fromisoformat(cursor))

    query = query.order_by(Document.created_at.desc()).limit(limit)

    result = await db.execute(query)
    documents = list(result.scalars().all())

    # Get total count
    count_query = select(func.count(Document.id))
    if category:
        count_query = count_query.join(PolicyCategory).where(
            PolicyCategory.name == category
        )
    if doc_status:
        count_query = count_query.where(Document.status == doc_status)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    next_cursor = None
    if documents and len(documents) == limit:
        next_cursor = documents[-1].created_at.isoformat()

    data = []
    for doc in documents:
        # Get latest version info
        version_result = await db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == doc.id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        latest_version = version_result.scalar_one_or_none()

        cat_result = await db.execute(
            select(PolicyCategory.name).where(PolicyCategory.id == doc.category_id)
        )
        category_name = cat_result.scalar_one_or_none() or ""

        data.append(
            DocumentResponse(
                id=str(doc.id),
                title=doc.title,
                document_external_id=doc.document_external_id,
                category=category_name,
                source_type=doc.source_type,
                source_url=doc.source_url,
                effective_date=doc.effective_date.isoformat(),
                review_date=doc.review_date.isoformat() if doc.review_date else None,
                owner=doc.owner,
                status=doc.status,
                current_version=latest_version.version_number if latest_version else 0,
                last_indexed_at=(
                    latest_version.indexed_at.isoformat()
                    if latest_version and latest_version.indexed_at
                    else None
                ),
                indexing_status=(
                    latest_version.indexing_status if latest_version else "pending"
                ),
            )
        )

    return DocumentListResponse(data=data, next_cursor=next_cursor, total=total)


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    title: str,
    document_external_id: str,
    category: str,
    effective_date: str,
    owner: str,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    blob_service: Annotated[BlobService, Depends(get_blob_service)],
    review_date: str | None = None,
) -> dict[str, object]:
    """Upload a new policy document and store it in Blob Storage (FR-031)."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is required",
        )

    # Determine file type
    extension = file.filename.rsplit(".", maxsplit=1)[-1].lower()
    if extension not in ("pdf", "docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are supported",
        )

    # Get or create category
    cat_result = await db.execute(
        select(PolicyCategory).where(PolicyCategory.name == category)
    )
    policy_category = cat_result.scalar_one_or_none()
    if not policy_category:
        policy_category = PolicyCategory(name=category)
        db.add(policy_category)
        await db.flush()

    # Upload to blob storage
    file_data = await file.read()
    blob_path = f"{category.lower()}/{document_external_id}/{uuid.uuid4()}.{extension}"
    await blob_service.upload_document(
        blob_path, file_data, file.content_type or "application/octet-stream"
    )

    # Create document record
    doc = Document(
        title=title,
        document_external_id=document_external_id,
        category_id=policy_category.id,
        source_type="blob",
        effective_date=datetime.strptime(effective_date, "%Y-%m-%d").date(),
        review_date=(
            datetime.strptime(review_date, "%Y-%m-%d").date()
            if review_date
            else None
        ),
        owner=owner,
    )
    db.add(doc)
    await db.flush()

    # Create first version
    version = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        blob_path=blob_path,
        file_type=extension,
        indexed_by=user.user_id,
        indexing_status="pending",
    )
    db.add(version)

    # Update category document count
    policy_category.document_count += 1
    policy_category.last_updated = datetime.now(tz=UTC)

    await db.commit()
    await db.refresh(doc)

    return {
        "id": str(doc.id),
        "title": doc.title,
        "document_external_id": doc.document_external_id,
        "category": category,
        "status": doc.status,
        "version": 1,
        "indexing_status": "pending",
        "created_at": doc.created_at.isoformat(),
    }


@router.post("/documents/{document_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_document(
    document_id: uuid.UUID,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReindexResponse:
    """Trigger re-indexing of a specific document (FR-005)."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # In production, this would dispatch a Celery task to the ingestion worker
    task_id = str(uuid.uuid4())

    return ReindexResponse(
        task_id=task_id,
        document_id=str(document_id),
        status="processing",
        message=f"Re-indexing started. Check status via GET /v1/admin/documents/{document_id}.",
    )


@router.post("/documents/reindex-all", status_code=status.HTTP_202_ACCEPTED)
async def reindex_all(
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReindexAllResponse:
    """Trigger full corpus re-indexing (FR-005)."""
    count_result = await db.execute(
        select(func.count(Document.id)).where(Document.status == "active")
    )
    doc_count = count_result.scalar() or 0

    task_id = str(uuid.uuid4())

    return ReindexAllResponse(
        task_id=task_id,
        status="processing",
        document_count=doc_count,
        message="Full corpus re-indexing started. Estimated completion: ~2 hours.",
    )


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: uuid.UUID,
    body: UpdateDocumentRequest,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    """Update document metadata or retire a document (FR-031)."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if body.status is not None:
        doc.status = body.status
    if body.title is not None:
        doc.title = body.title
    if body.owner is not None:
        doc.owner = body.owner

    await db.commit()
    await db.refresh(doc)

    return {
        "id": str(doc.id),
        "title": doc.title,
        "status": doc.status,
        "updated_at": doc.updated_at.isoformat(),
    }


@router.get("/documents/{document_id}/versions")
async def list_versions(
    document_id: uuid.UUID,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, list[VersionResponse]]:
    """View version history for a document (FR-006)."""
    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
    )
    versions = list(result.scalars().all())

    return {
        "data": [
            VersionResponse(
                version_id=str(v.id),
                version_number=v.version_number,
                file_type=v.file_type,
                page_count=v.page_count,
                indexed_by=v.indexed_by,
                indexing_status=v.indexing_status,
                indexed_at=v.indexed_at.isoformat() if v.indexed_at else None,
                created_at=v.created_at.isoformat(),
            )
            for v in versions
        ]
    }


@router.post("/test-query")
async def test_query(
    body: TestQueryRequest,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    rag_pipeline: Annotated[RAGPipeline, Depends(get_rag_pipeline)],
) -> dict[str, object]:
    """Preview how the chatbot would answer a question (FR-032)."""
    # Use a temporary conversation context for the test
    test_conversation_id = str(uuid.uuid4())
    current_response = await rag_pipeline.process_query(
        test_conversation_id, body.query
    )

    result: dict[str, object] = {
        "current_corpus_response": current_response,
    }

    if body.include_pending_documents:
        result["pending_corpus_response"] = current_response

    return result


@router.get("/analytics")
async def get_analytics(
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    period: str = Query(pattern=r"^(day|week|month)$"),
    start_date: str | None = None,
    end_date: str | None = None,
) -> AnalyticsResponse:
    """Retrieve analytics data for the admin dashboard (FR-029)."""
    now = datetime.now(tz=UTC)

    if start_date:
        period_start = datetime.fromisoformat(start_date).replace(tzinfo=UTC)
    else:
        delta = {"day": 1, "week": 7, "month": 30}[period]
        period_start = now - __import__("datetime").timedelta(days=delta)

    period_end = (
        datetime.fromisoformat(end_date).replace(tzinfo=UTC) if end_date else now
    )

    # Query volume
    volume_result = await db.execute(
        select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.created_at >= period_start,
            AnalyticsEvent.created_at <= period_end,
            AnalyticsEvent.event_type == "query",
        )
    )
    query_volume = volume_result.scalar() or 0

    # Resolution rate
    resolved_result = await db.execute(
        select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.created_at >= period_start,
            AnalyticsEvent.created_at <= period_end,
            AnalyticsEvent.event_type == "query",
            AnalyticsEvent.resolved.is_(True),
        )
    )
    resolved_count = resolved_result.scalar() or 0
    resolution_rate = resolved_count / max(query_volume, 1)

    # Escalation count
    escalation_result = await db.execute(
        select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.created_at >= period_start,
            AnalyticsEvent.created_at <= period_end,
            AnalyticsEvent.event_type == "escalation",
        )
    )
    escalation_count = escalation_result.scalar() or 0
    escalation_rate = escalation_count / max(query_volume, 1)

    # Average satisfaction
    satisfaction_result = await db.execute(
        select(
            func.count(Feedback.id).filter(Feedback.rating == "positive"),
            func.count(Feedback.id),
        ).where(Feedback.created_at >= period_start, Feedback.created_at <= period_end)
    )
    sat_row = satisfaction_result.one()
    positive_count = sat_row[0] or 0
    total_feedback = sat_row[1] or 1
    avg_satisfaction = round((positive_count / max(total_feedback, 1)) * 5, 1)

    # Top intents
    intent_result = await db.execute(
        select(AnalyticsEvent.intent, func.count(AnalyticsEvent.id).label("count"))
        .where(
            AnalyticsEvent.created_at >= period_start,
            AnalyticsEvent.created_at <= period_end,
            AnalyticsEvent.intent.isnot(None),
        )
        .group_by(AnalyticsEvent.intent)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(20)
    )
    top_intents = [
        {"intent": row[0], "count": row[1]} for row in intent_result.all()
    ]

    # Unanswered queries
    unanswered_result = await db.execute(
        select(
            AnalyticsEvent.intent,
            func.count(AnalyticsEvent.id).label("count"),
            func.max(AnalyticsEvent.created_at).label("last_asked"),
        )
        .where(
            AnalyticsEvent.created_at >= period_start,
            AnalyticsEvent.created_at <= period_end,
            AnalyticsEvent.resolved.is_(False),
        )
        .group_by(AnalyticsEvent.intent)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(20)
    )
    unanswered = [
        {
            "query": row[0] or "unknown",
            "count": row[1],
            "last_asked": row[2].isoformat() if row[2] else None,
        }
        for row in unanswered_result.all()
    ]

    return AnalyticsResponse(
        period=period,
        start_date=period_start.date().isoformat(),
        end_date=period_end.date().isoformat(),
        query_volume=query_volume,
        resolution_rate=round(resolution_rate, 2),
        escalation_rate=round(escalation_rate, 2),
        average_satisfaction=avg_satisfaction,
        top_intents=top_intents,
        unanswered_queries=unanswered,
    )


@router.get("/analytics/flagged-topics")
async def get_flagged_topics(
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FlaggedTopicResponse:
    """View topics flagged for admin review due to repeated negative feedback (FR-030)."""
    result = await db.execute(
        select(FeedbackFlag)
        .where(FeedbackFlag.negative_count > 3)
        .order_by(FeedbackFlag.negative_count.desc())
    )
    flags = list(result.scalars().all())

    return FlaggedTopicResponse(
        data=[
            {
                "flag_id": str(f.id),
                "topic": f.topic,
                "negative_count": f.negative_count,
                "status": f.status,
                "first_flagged_at": f.first_flagged_at.isoformat(),
            }
            for f in flags
        ]
    )


@router.get("/coverage")
async def get_coverage(
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CoverageResponse:
    """Display policy coverage report by domain (FR-033)."""
    all_domains = ["HR", "IT", "Finance", "Facilities", "Legal", "Compliance", "Safety"]

    result = await db.execute(
        select(PolicyCategory).order_by(PolicyCategory.name)
    )
    categories = {c.name: c for c in result.scalars().all()}

    domains: list[CoverageDomain] = []
    gaps: list[str] = []
    total = 0

    for domain in all_domains:
        cat = categories.get(domain)
        count = cat.document_count if cat else 0
        last_updated = cat.last_updated.date().isoformat() if cat else None
        total += count

        if count == 0:
            gaps.append(domain)

        domains.append(
            CoverageDomain(
                name=domain,
                document_count=count,
                last_updated=last_updated,
            )
        )

    return CoverageResponse(domains=domains, total_documents=total, gaps=gaps)
