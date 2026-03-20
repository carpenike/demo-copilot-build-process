"""SQLAlchemy ORM models — maps to all 10 entities in data-model.md."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="Employee")
    manager_email: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="user")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    review_date: Mapped[date | None] = mapped_column(Date)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    blob_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    uploaded_by: Mapped[str] = mapped_column(String(320), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    document: Mapped["Document"] = relationship(back_populates="versions")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    escalation_ticket_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[dict | None] = mapped_column(JSONB)  # type: ignore[assignment]
    intent: Mapped[dict | None] = mapped_column(JSONB)  # type: ignore[assignment]
    response_type: Mapped[str | None] = mapped_column(String(50))
    checklist: Mapped[dict | None] = mapped_column(JSONB)  # type: ignore[assignment]
    wayfinding: Mapped[dict | None] = mapped_column(JSONB)  # type: ignore[assignment]
    token_count: Mapped[int | None] = mapped_column(Integer)
    response_time_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    feedback: Mapped["Feedback | None"] = relationship(back_populates="message", uselist=False)


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (UniqueConstraint("message_id", name="uq_feedback_message_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, unique=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    rating: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    message: Mapped["Message"] = relationship(back_populates="feedback")
    user: Mapped["User"] = relationship(back_populates="feedbacks")


class FlaggedTopic(Base):
    __tablename__ = "flagged_topics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    negative_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sample_comments: Mapped[dict | None] = mapped_column(JSONB)  # type: ignore[assignment]
    first_flagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AnalyticsDaily(Base):
    __tablename__ = "analytics_daily"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    total_queries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resolved_queries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    escalated_queries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    no_match_queries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    positive_feedback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negative_feedback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_response_time_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )


class IntentCount(Base):
    __tablename__ = "intent_counts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    intent_label: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UnansweredQuery(Base):
    __tablename__ = "unanswered_queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    detected_intent: Mapped[str | None] = mapped_column(String(200))
    detected_domain: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
