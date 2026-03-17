"""Document-related ORM models for the policy corpus."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class PolicyCategory(Base):
    """Policy domain categories used for document classification and coverage reporting."""

    __tablename__ = "policy_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    document_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    documents: Mapped[list["Document"]] = relationship(back_populates="category")


class Document(Base):
    """Metadata record for a policy document in the corpus."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_external_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policy_categories.id"))
    source_type: Mapped[str] = mapped_column(
        Enum("sharepoint", "wordpress", "blob", name="source_type_enum", create_constraint=True),
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(String(2048))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    review_date: Mapped[date | None] = mapped_column(Date)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "retired", name="document_status_enum", create_constraint=True),
        default="active",
        server_default="active",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category: Mapped["PolicyCategory"] = relationship(back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document", order_by="DocumentVersion.version_number.desc()"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")


class DocumentVersion(Base):
    """Version history entry for a document — tracks each re-indexing."""

    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    blob_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(
        Enum("pdf", "docx", "html", name="file_type_enum", create_constraint=True),
        nullable=False,
    )
    page_count: Mapped[int | None] = mapped_column(Integer)
    indexed_by: Mapped[str | None] = mapped_column(String(255))
    indexing_status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "processing",
            "completed",
            "failed",
            name="indexing_status_enum",
            create_constraint=True,
        ),
        default="pending",
        server_default="pending",
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="versions")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="version")


class DocumentChunk(Base):
    """Metadata for a semantic chunk of a document — content lives in Azure AI Search."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_heading: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ai_search_doc_id: Mapped[str | None] = mapped_column(String(255))
    token_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="chunks")
    version: Mapped["DocumentVersion"] = relationship(back_populates="chunks")
