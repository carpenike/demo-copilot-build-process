"""Admin API endpoints for document management, analytics, and test queries.

All endpoints require the PolicyAdmin app role (enforced by require_admin dependency).
"""

from __future__ import annotations

import uuid
from datetime import date

import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import (
    AdminUserDep,
    DbDep,
    DocServiceDep,
    FeedbackServiceDep,
    LLMDep,
    SearchDep,
    SettingsDep,
)
from app.core import rag_pipeline
from app.models.schemas import (
    AnalyticsPeriod,
    AnalyticsResponse,
    AnalyticsSummary,
    CategoryCoverage,
    CoverageResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentRetireResponse,
    DocumentStatus,
    DocumentUploadResponse,
    DocumentVersionsResponse,
    FlaggedTopic,
    FlaggedTopicsResponse,
    ProblemDetail,
    ReindexResponse,
    ReindexStatusResponse,
    TestQueryRequest,
    TestQueryResponse,
    TestQueryResult,
    TopIntent,
    UnansweredQueriesResponse,
    VersionInfo,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/admin", tags=["admin"])

ALLOWED_EXTENSIONS = frozenset({".pdf", ".docx", ".html", ".htm"})
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    admin: AdminUserDep,
    db: DbDep,
    doc_service: DocServiceDep,
    cursor: str | None = None,
    limit: int = 20,
    category: str | None = None,
    document_status: str | None = None,
) -> DocumentListResponse:
    """List all policy documents with metadata and status."""
    if limit < 1 or limit > 100:
        limit = 20

    documents, next_cursor, total = await doc_service.list_documents(
        db, category=category, status=document_status, limit=limit, cursor=cursor
    )

    return DocumentListResponse(
        data=[
            DocumentResponse(
                id=d["id"],
                title=d["title"],
                document_external_id=d["document_external_id"],
                category=d["category"],
                effective_date=d["effective_date"],
                review_date=d["review_date"],
                owner=d["owner"],
                source_url=d["source_url"],
                status=DocumentStatus(d["status"]),
                current_version=d["current_version"],
                created_at=d["created_at"],
                updated_at=d["updated_at"],
            )
            for d in documents
        ],
        next_cursor=next_cursor,
        total=total,
    )


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={400: {"model": ProblemDetail}, 409: {"model": ProblemDetail}},
)
async def upload_document(
    admin: AdminUserDep,
    db: DbDep,
    doc_service: DocServiceDep,
    feedback_service: FeedbackServiceDep,
    file: UploadFile = File(...),
    title: str = Form(...),
    document_external_id: str = Form(...),
    category: str = Form(...),
    effective_date: date = Form(...),
    owner: str = Form(...),
    review_date: date | None = Form(default=None),
    source_url: str | None = Form(default=None),
) -> DocumentUploadResponse:
    """Upload a new policy document and trigger indexing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 50 MB limit")

    admin_id = admin.get("preferred_username", admin.get("sub", "unknown"))

    try:
        document = await doc_service.upload_document(
            db,
            file_content=content,
            filename=file.filename,
            title=title,
            document_external_id=document_external_id,
            category_name=category,
            effective_date=effective_date,
            review_date=review_date,
            owner=owner,
            source_url=source_url,
            uploaded_by=admin_id,
        )
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document with external ID '{document_external_id}' already exists",
            ) from e
        raise

    await feedback_service.record_analytics_event(
        db,
        event_type="document_indexed",
        document_id=document.id,
        metadata={"title": title, "category": category},
    )
    await db.commit()

    return DocumentUploadResponse(
        id=document.id,
        title=document.title,
        status=DocumentStatus.PROCESSING,
        version=1,
        message="Document uploaded. Indexing has been queued and will complete shortly.",
    )


@router.put(
    "/documents/{document_id}",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def update_document(
    document_id: uuid.UUID,
    admin: AdminUserDep,
    db: DbDep,
    doc_service: DocServiceDep,
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    """Upload a new version of an existing document and trigger re-indexing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    admin_id = admin.get("preferred_username", admin.get("sub", "unknown"))

    document, version = await doc_service.upload_new_version(
        db,
        document_id=document_id,
        file_content=content,
        filename=file.filename,
        uploaded_by=admin_id,
    )

    return DocumentUploadResponse(
        id=document.id,
        title=document.title,
        status=DocumentStatus.PROCESSING,
        version=version.version_number,
        message="New version uploaded. Re-indexing has been queued.",
    )


@router.post(
    "/documents/{document_id}/retire",
    response_model=DocumentRetireResponse,
)
async def retire_document(
    document_id: uuid.UUID,
    admin: AdminUserDep,
    db: DbDep,
    doc_service: DocServiceDep,
    search_service: SearchDep,
) -> DocumentRetireResponse:
    """Retire a document from the active corpus."""
    document = await doc_service.retire_document(db, document_id)

    await search_service.delete_document_chunks(str(document_id))

    return DocumentRetireResponse(
        id=document.id,
        title=document.title,
        status=DocumentStatus.RETIRED,
        message="Document retired. It will no longer be used in chatbot answers.",
    )


@router.post(
    "/documents/{document_id}/reindex",
    response_model=ReindexResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reindex_document(
    document_id: uuid.UUID,
    admin: AdminUserDep,
) -> ReindexResponse:
    """Trigger re-indexing of a single document."""
    # In production, this would enqueue a Celery task
    return ReindexResponse(
        id=document_id,
        status="processing",
        message="Re-indexing queued.",
    )


@router.post(
    "/reindex-all",
    response_model=ReindexResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reindex_all(
    admin: AdminUserDep,
    db: DbDep,
    doc_service: DocServiceDep,
) -> ReindexResponse:
    """Trigger full corpus re-indexing."""
    # In production, this would enqueue a Celery task
    _docs, _, total = await doc_service.list_documents(db, status="active", limit=1)

    return ReindexResponse(
        status="processing",
        total_documents=total,
        message="Full corpus re-indexing has been queued. This may take up to 2 hours.",
    )


@router.get("/reindex-status", response_model=ReindexStatusResponse)
async def reindex_status(
    admin: AdminUserDep,
) -> ReindexStatusResponse:
    """Check the status of an ongoing re-indexing operation."""
    from datetime import UTC, datetime

    # In production, this would check Celery task state
    return ReindexStatusResponse(
        status="idle",
        documents_processed=0,
        documents_total=0,
        started_at=datetime.now(UTC),
    )


@router.get(
    "/documents/{document_id}/versions",
    response_model=DocumentVersionsResponse,
)
async def document_versions(
    document_id: uuid.UUID,
    admin: AdminUserDep,
    db: DbDep,
    doc_service: DocServiceDep,
) -> DocumentVersionsResponse:
    """View version history of a document."""
    versions = await doc_service.get_document_versions(db, document_id)

    return DocumentVersionsResponse(
        document_id=document_id,
        versions=[
            VersionInfo(
                version_number=v.version_number,
                status=v.status,
                indexed_by=v.indexed_by,
                indexed_at=v.indexed_at,
                created_at=v.created_at,
            )
            for v in versions
        ],
    )


@router.post("/test-query", response_model=TestQueryResponse)
async def test_query(
    body: TestQueryRequest,
    admin: AdminUserDep,
    db: DbDep,
    llm_service: LLMDep,
    search_service: SearchDep,
    settings: SettingsDep,
) -> TestQueryResponse:
    """Test how the chatbot would answer a question."""
    result = await rag_pipeline.run_pipeline(
        query=body.query,
        llm_service=llm_service,
        search_service=search_service,
        confidence_threshold=settings.rag_confidence_threshold,
        top_k=settings.rag_top_k,
    )

    live_response = TestQueryResult(
        content=result.response_body.content,
        citations=result.response_body.citations,
        confidence=result.response_body.confidence,
    )

    return TestQueryResponse(
        live_response=live_response,
        staged_response=None,
    )


@router.get("/coverage", response_model=CoverageResponse)
async def coverage(
    admin: AdminUserDep,
    db: DbDep,
    doc_service: DocServiceDep,
) -> CoverageResponse:
    """Display policy domain coverage report."""
    categories = await doc_service.get_coverage(db)

    total = sum(c["document_count"] for c in categories)
    gaps = [c["name"] for c in categories if c["status"] == "gap"]

    return CoverageResponse(
        categories=[
            CategoryCoverage(
                name=c["name"],
                document_count=c["document_count"],
                status=c["status"],
            )
            for c in categories
        ],
        total_documents=total,
        gaps=gaps,
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def analytics(
    admin: AdminUserDep,
    db: DbDep,
    feedback_service: FeedbackServiceDep,
    start_date: date = date(2026, 1, 1),
    end_date: date = date(2026, 12, 31),
    granularity: str = "daily",
) -> AnalyticsResponse:
    """Retrieve analytics dashboard data."""
    summary_data = await feedback_service.get_analytics(
        db, start_date=start_date, end_date=end_date
    )
    top_intents_data = await feedback_service.get_top_intents(
        db, start_date=start_date, end_date=end_date
    )

    return AnalyticsResponse(
        period=AnalyticsPeriod(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            granularity=granularity,
        ),
        summary=AnalyticsSummary(**summary_data),
        top_intents=[TopIntent(**t) for t in top_intents_data],
        volume_by_period=[],
    )


@router.get("/analytics/unanswered", response_model=UnansweredQueriesResponse)
async def unanswered_queries(
    admin: AdminUserDep,
) -> UnansweredQueriesResponse:
    """View log of unanswered queries."""
    # In production, this would query the analytics_events table
    return UnansweredQueriesResponse(data=[])


@router.get("/analytics/flagged", response_model=FlaggedTopicsResponse)
async def flagged_topics(
    admin: AdminUserDep,
    db: DbDep,
    feedback_service: FeedbackServiceDep,
) -> FlaggedTopicsResponse:
    """View topics flagged for review due to repeated negative feedback."""
    topics = await feedback_service.get_flagged_topics(db)

    return FlaggedTopicsResponse(
        flagged_topics=[
            FlaggedTopic(
                topic=t["topic"],
                negative_feedback_count=t["negative_feedback_count"],
                sample_queries=t["sample_queries"],
                sample_comments=t["sample_comments"],
            )
            for t in topics
        ]
    )
