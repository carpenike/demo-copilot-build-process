"""Admin endpoints — document management, reindex, test-query, coverage."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.chat import _get_db
from app.core.auth import CurrentUser, require_admin
from app.models.database import Document, DocumentVersion
from app.models.schemas import (
    CategoryCoverage,
    CoverageResponse,
    DocumentCreateResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentPatchRequest,
    DocumentPatchResponse,
    DocumentResponse,
    DocumentUpdateResponse,
    DocumentVersionItem,
    QueryPreviewAnswer,
    QueryPreviewRequest,
    QueryPreviewResponse,
    ReindexCorpusResponse,
    ReindexDocumentResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/admin", tags=["admin"])

_VALID_CATEGORIES = frozenset(
    {"HR", "IT", "Finance", "Facilities", "Legal", "Compliance", "Safety"}
)
_VALID_FILE_TYPES = frozenset({"pdf", "docx", "html"})
_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# ---------------------------------------------------------------------------
# GET /v1/admin/documents
# ---------------------------------------------------------------------------
@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    cursor: str | None = None,
    limit: int = 20,
    category: str | None = None,
    doc_status: str | None = None,
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """List all documents in the policy corpus with metadata."""
    limit = min(limit, 100)
    query = select(Document).order_by(Document.created_at.desc()).limit(limit + 1)

    if category:
        query = query.where(Document.category == category)
    if doc_status:
        query = query.where(Document.status == doc_status)
    if cursor:
        try:
            cursor_id = uuid.UUID(cursor)
            query = query.where(Document.id < cursor_id)
        except ValueError:
            pass

    result = await db.execute(query)
    docs = list(result.scalars().all())
    has_more = len(docs) > limit
    if has_more:
        docs = docs[:limit]

    return DocumentListResponse(
        data=[
            DocumentResponse(
                id=d.id,
                title=d.title,
                category=d.category,
                status=d.status,
                effective_date=d.effective_date,
                review_date=d.review_date,
                owner=d.owner,
                source_url=d.source_url,
                current_version=d.current_version,
                last_indexed_at=d.last_indexed_at,
                page_count=d.page_count,
                created_at=d.created_at,
            )
            for d in docs
        ],
        next_cursor=str(docs[-1].id) if has_more else None,
    )


# ---------------------------------------------------------------------------
# GET /v1/admin/documents/{document_id}
# ---------------------------------------------------------------------------
@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: uuid.UUID,
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Get detailed information for a specific document, including version history."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    ver_result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
    )
    versions = ver_result.scalars().all()

    return DocumentDetailResponse(
        id=doc.id,
        title=doc.title,
        category=doc.category,
        status=doc.status,
        effective_date=doc.effective_date,
        review_date=doc.review_date,
        owner=doc.owner,
        source_url=doc.source_url,
        current_version=doc.current_version,
        last_indexed_at=doc.last_indexed_at,
        page_count=doc.page_count,
        created_at=doc.created_at,
        versions=[
            DocumentVersionItem(
                version=v.version_number,
                uploaded_at=v.uploaded_at,
                uploaded_by=v.uploaded_by,
                is_active=v.is_active,
                blob_path=v.blob_path,
            )
            for v in versions
        ],
    )


# ---------------------------------------------------------------------------
# POST /v1/admin/documents
# ---------------------------------------------------------------------------
@router.post(
    "/documents",
    response_model=DocumentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    request: Request,
    file: UploadFile,
    title: str = Form(..., max_length=255),
    category: str = Form(...),
    effective_date: str = Form(...),
    owner: str = Form(..., max_length=255),
    review_date: str | None = Form(None),
    source_url: str | None = Form(None, max_length=2048),
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Upload a new policy document and trigger indexing."""
    # Validate category
    if category not in _VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category must be one of: {', '.join(sorted(_VALID_CATEGORIES))}",
        )

    # Validate file type
    extension = (file.filename or "").rsplit(".", maxsplit=1)[-1].lower()
    if extension not in _VALID_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(_VALID_FILE_TYPES))}",
        )

    # Check file size
    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds maximum size of 50MB",
        )

    # Check duplicate title
    existing = await db.execute(select(Document).where(Document.title == title))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document with same title already exists",
        )

    from datetime import date as date_type

    eff_date = date_type.fromisoformat(effective_date)
    rev_date = date_type.fromisoformat(review_date) if review_date else None

    doc = Document(
        title=title,
        category=category,
        effective_date=eff_date,
        review_date=rev_date,
        owner=owner,
        source_url=source_url,
        current_version=1,
    )
    db.add(doc)
    await db.flush()

    blob_path = f"{category}/{doc.id}/1.{extension}"
    version = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        blob_path=blob_path,
        file_type=extension,
        file_size_bytes=len(content),
        is_active=True,
        uploaded_by=admin.email,
    )
    db.add(version)

    # Upload to blob storage
    await request.app.state.blob_service.upload(
        blob_path, content, file.content_type or "application/octet-stream"
    )

    # Trigger indexing
    await request.app.state.search_service.reindex_document(str(doc.id))

    return DocumentCreateResponse(
        id=doc.id,
        title=doc.title,
        category=doc.category,
        status=doc.status,
        effective_date=doc.effective_date,
        owner=doc.owner,
        version=1,
        indexing_status="in_progress",
        created_at=doc.created_at,
    )


# ---------------------------------------------------------------------------
# PUT /v1/admin/documents/{document_id}
# ---------------------------------------------------------------------------
@router.put("/documents/{document_id}", response_model=DocumentUpdateResponse)
async def update_document(
    document_id: uuid.UUID,
    request: Request,
    file: UploadFile,
    effective_date: str | None = Form(None),
    review_date: str | None = Form(None),
    owner: str | None = Form(None),
    source_url: str | None = Form(None, max_length=2048),
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Upload a new version of an existing document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    extension = (file.filename or "").rsplit(".", maxsplit=1)[-1].lower()
    if extension not in _VALID_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(_VALID_FILE_TYPES))}",
        )

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds maximum size of 50MB",
        )

    # Deactivate all previous versions
    ver_result = await db.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == document_id)
    )
    for v in ver_result.scalars().all():
        v.is_active = False

    new_version = doc.current_version + 1
    doc.current_version = new_version
    doc.updated_at = datetime.now(UTC)

    from datetime import date as date_type

    if effective_date:
        doc.effective_date = date_type.fromisoformat(effective_date)
    if review_date:
        doc.review_date = date_type.fromisoformat(review_date)
    if owner:
        doc.owner = owner
    if source_url is not None:
        doc.source_url = source_url

    blob_path = f"{doc.category}/{doc.id}/{new_version}.{extension}"
    version = DocumentVersion(
        document_id=doc.id,
        version_number=new_version,
        blob_path=blob_path,
        file_type=extension,
        file_size_bytes=len(content),
        is_active=True,
        uploaded_by=admin.email,
    )
    db.add(version)

    await request.app.state.blob_service.upload(
        blob_path, content, file.content_type or "application/octet-stream"
    )
    await request.app.state.search_service.reindex_document(str(doc.id))

    return DocumentUpdateResponse(
        id=doc.id,
        title=doc.title,
        version=new_version,
        indexing_status="in_progress",
        updated_at=doc.updated_at,
    )


# ---------------------------------------------------------------------------
# PATCH /v1/admin/documents/{document_id}
# ---------------------------------------------------------------------------
@router.patch("/documents/{document_id}", response_model=DocumentPatchResponse)
async def patch_document(
    document_id: uuid.UUID,
    body: DocumentPatchRequest,
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Update document metadata or retire a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if body.status is not None:
        if body.status not in {"active", "retired"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status must be 'active' or 'retired'",
            )
        doc.status = body.status
    if body.title is not None:
        doc.title = body.title
    if body.category is not None:
        if body.category not in _VALID_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category must be one of: {', '.join(sorted(_VALID_CATEGORIES))}",
            )
        doc.category = body.category
    if body.effective_date is not None:
        doc.effective_date = body.effective_date
    if body.review_date is not None:
        doc.review_date = body.review_date
    if body.owner is not None:
        doc.owner = body.owner
    if body.source_url is not None:
        doc.source_url = body.source_url

    doc.updated_at = datetime.now(UTC)

    return DocumentPatchResponse(
        id=doc.id,
        title=doc.title,
        status=doc.status,
        updated_at=doc.updated_at,
    )


# ---------------------------------------------------------------------------
# POST /v1/admin/documents/{document_id}/reindex
# ---------------------------------------------------------------------------
@router.post("/documents/{document_id}/reindex", response_model=ReindexDocumentResponse)
async def reindex_document(
    document_id: uuid.UUID,
    request: Request,
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Trigger re-indexing of a single document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    await request.app.state.search_service.reindex_document(str(document_id))
    return ReindexDocumentResponse(
        document_id=document_id,
        indexing_status="in_progress",
    )


# ---------------------------------------------------------------------------
# POST /v1/admin/reindex
# ---------------------------------------------------------------------------
@router.post("/reindex", response_model=ReindexCorpusResponse)
async def reindex_corpus(
    request: Request,
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Trigger full corpus re-indexing."""
    count_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.status == "active")
    )
    doc_count = count_result.scalar() or 0

    await request.app.state.search_service.reindex_all()
    return ReindexCorpusResponse(
        indexing_status="in_progress",
        document_count=doc_count,
    )


# ---------------------------------------------------------------------------
# POST /v1/admin/test-query
# ---------------------------------------------------------------------------
@router.post("/test-query", response_model=QueryPreviewResponse)
async def admin_test_query(
    body: QueryPreviewRequest,
    request: Request,
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Preview how the chatbot would answer a question."""
    # Live answer
    chunks = await request.app.state.search_service.hybrid_search(body.query, top_k=5)
    live_result = await request.app.state.openai_service.generate_answer(
        query=body.query,
        context_chunks=chunks,
    )
    live_answer = QueryPreviewAnswer(
        content=live_result.get("content", ""),
        citations=live_result.get("citations", []),
    )

    preview_answer: QueryPreviewAnswer | None = None
    if body.draft_document_id:
        result = await db.execute(select(Document).where(Document.id == body.draft_document_id))
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft document not found",
            )
        # In production, include draft document in search context
        preview_answer = QueryPreviewAnswer(
            content="Preview with draft document...",
            citations=[],
        )

    return QueryPreviewResponse(live_answer=live_answer, preview_answer=preview_answer)


# ---------------------------------------------------------------------------
# GET /v1/admin/coverage
# ---------------------------------------------------------------------------
@router.get("/coverage", response_model=CoverageResponse)
async def get_coverage(
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Display policy coverage by domain."""
    categories_data: list[CategoryCoverage] = []
    gaps: list[str] = []
    total_docs = 0
    total_pages = 0

    for cat in sorted(_VALID_CATEGORIES):
        result = await db.execute(
            select(
                func.count(Document.id),
                func.coalesce(func.sum(Document.page_count), 0),
                func.max(Document.last_indexed_at),
            ).where(Document.category == cat, Document.status == "active")
        )
        row = result.one()
        doc_count: int = row[0]  # type: ignore[assignment]
        page_count: int = row[1]  # type: ignore[assignment]
        last_indexed: datetime | None = row[2]  # type: ignore[assignment]

        cat_status = "covered" if doc_count > 0 else "gap"
        if cat_status == "gap":
            gaps.append(cat)
        total_docs += doc_count
        total_pages += page_count

        categories_data.append(
            CategoryCoverage(
                category=cat,
                document_count=doc_count,
                total_pages=page_count,
                last_indexed_at=last_indexed,
                status=cat_status,
            )
        )

    return CoverageResponse(
        categories=categories_data,
        total_documents=total_docs,
        total_pages=total_pages,
        categories_with_gaps=gaps,
    )
