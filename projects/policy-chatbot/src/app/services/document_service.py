"""Document service for policy document management and blob storage.

Handles document CRUD operations, blob upload/download, and metadata
management in PostgreSQL. Uses lazy Azure SDK imports.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    Document,
    DocumentVersion,
    PolicyCategory,
)

if TYPE_CHECKING:
    from app.config import Settings

logger = structlog.get_logger()


class DocumentService:
    """Manages policy document lifecycle — upload, index, retire."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._blob_client: Any = None

    def _get_blob_service(self) -> Any:
        """Lazily initialize the Azure Blob Storage client."""
        if self._blob_client is None:
            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import BlobServiceClient

            credential = DefaultAzureCredential()
            self._blob_client = BlobServiceClient(
                account_url=self._settings.azure_storage_account_url,
                credential=credential,
            )
        return self._blob_client

    async def upload_document(
        self,
        db: AsyncSession,
        *,
        file_content: bytes,
        filename: str,
        title: str,
        document_external_id: str,
        category_name: str,
        effective_date: date,
        review_date: date | None,
        owner: str,
        source_url: str | None,
        uploaded_by: str,
    ) -> Document:
        """Upload a new policy document to blob storage and create DB records."""
        category = await self._get_or_create_category(db, category_name)

        doc_id = uuid.uuid4()
        blob_path = f"{doc_id}/{filename}"

        blob_service = self._get_blob_service()
        container = blob_service.get_container_client(self._settings.azure_storage_container_raw)
        container.upload_blob(name=blob_path, data=file_content, overwrite=True)

        document = Document(
            id=doc_id,
            title=title,
            document_external_id=document_external_id,
            category_id=category.id,
            effective_date=effective_date,
            review_date=review_date,
            owner=owner,
            source_url=source_url,
            blob_path=blob_path,
            status="processing",
        )
        db.add(document)

        version = DocumentVersion(
            document_id=doc_id,
            version_number=1,
            blob_path=blob_path,
            indexed_by=uploaded_by,
            status="processing",
        )
        db.add(version)

        await self._increment_category_count(db, category.id)
        await db.commit()
        await db.refresh(document)

        logger.info("document_uploaded", document_id=str(doc_id), title=title)
        return document

    async def upload_new_version(
        self,
        db: AsyncSession,
        *,
        document_id: uuid.UUID,
        file_content: bytes,
        filename: str,
        uploaded_by: str,
    ) -> tuple[Document, DocumentVersion]:
        """Upload a new version of an existing document."""
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one()

        current_version_result = await db.execute(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document_id
            )
        )
        current_max = current_version_result.scalar() or 0
        new_version_number = current_max + 1

        blob_path = f"{document_id}/{filename}"
        blob_service = self._get_blob_service()
        container = blob_service.get_container_client(self._settings.azure_storage_container_raw)
        container.upload_blob(name=blob_path, data=file_content, overwrite=True)

        await db.execute(
            update(DocumentVersion)
            .where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.status == "indexed",
            )
            .values(status="superseded")
        )

        version = DocumentVersion(
            document_id=document_id,
            version_number=new_version_number,
            blob_path=blob_path,
            indexed_by=uploaded_by,
            status="processing",
        )
        db.add(version)

        document.status = "processing"
        document.blob_path = blob_path
        document.updated_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(document)
        await db.refresh(version)

        logger.info(
            "document_version_uploaded",
            document_id=str(document_id),
            version=new_version_number,
        )
        return document, version

    async def retire_document(self, db: AsyncSession, document_id: uuid.UUID) -> Document:
        """Mark a document as retired so it is excluded from chatbot answers."""
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one()

        document.status = "retired"
        document.updated_at = datetime.now(UTC)

        await self._decrement_category_count(db, document.category_id)
        await db.commit()
        await db.refresh(document)

        logger.info("document_retired", document_id=str(document_id))
        return document

    async def list_documents(
        self,
        db: AsyncSession,
        *,
        category: str | None = None,
        status: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, int]:
        """List documents with optional filtering and cursor pagination."""
        query = select(Document, PolicyCategory.name.label("category_name")).join(
            PolicyCategory, Document.category_id == PolicyCategory.id
        )

        if category:
            query = query.where(PolicyCategory.name == category)
        if status:
            query = query.where(Document.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        if cursor:
            query = query.where(Document.created_at < datetime.fromisoformat(cursor))

        query = query.order_by(Document.created_at.desc()).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        documents: list[dict[str, Any]] = []
        for row in rows:
            doc = row[0]
            cat_name = row[1]

            version_result = await db.execute(
                select(func.max(DocumentVersion.version_number)).where(
                    DocumentVersion.document_id == doc.id
                )
            )
            current_version = version_result.scalar() or 0

            documents.append(
                {
                    "id": doc.id,
                    "title": doc.title,
                    "document_external_id": doc.document_external_id,
                    "category": cat_name,
                    "effective_date": doc.effective_date,
                    "review_date": doc.review_date,
                    "owner": doc.owner,
                    "source_url": doc.source_url,
                    "status": doc.status,
                    "current_version": current_version,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at,
                }
            )

        next_cursor = documents[-1]["created_at"].isoformat() if len(documents) == limit else None

        return documents, next_cursor, total

    async def get_document_versions(
        self, db: AsyncSession, document_id: uuid.UUID
    ) -> list[DocumentVersion]:
        """Get all versions of a document, ordered by version number descending."""
        result = await db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_coverage(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Get document count per policy category for the coverage report."""
        result = await db.execute(select(PolicyCategory).order_by(PolicyCategory.name))
        categories = result.scalars().all()

        return [
            {
                "name": cat.name,
                "document_count": cat.document_count,
                "status": "covered" if cat.document_count > 0 else "gap",
            }
            for cat in categories
        ]

    async def download_document(self, blob_path: str) -> bytes:
        """Download raw document content from blob storage."""
        blob_service = self._get_blob_service()
        container = blob_service.get_container_client(self._settings.azure_storage_container_raw)
        blob = container.get_blob_client(blob_path)
        return blob.download_blob().readall()  # type: ignore[no-any-return]

    async def _get_or_create_category(self, db: AsyncSession, name: str) -> PolicyCategory:
        """Get an existing category or create it if missing."""
        result = await db.execute(select(PolicyCategory).where(PolicyCategory.name == name))
        category = result.scalar_one_or_none()
        if category is None:
            category = PolicyCategory(name=name, description=f"{name} policy domain")
            db.add(category)
            await db.flush()
        return category

    async def _increment_category_count(self, db: AsyncSession, category_id: uuid.UUID) -> None:
        await db.execute(
            update(PolicyCategory)
            .where(PolicyCategory.id == category_id)
            .values(document_count=PolicyCategory.document_count + 1)
        )

    async def _decrement_category_count(self, db: AsyncSession, category_id: uuid.UUID) -> None:
        await db.execute(
            update(PolicyCategory)
            .where(PolicyCategory.id == category_id)
            .values(document_count=func.greatest(PolicyCategory.document_count - 1, 0))
        )
