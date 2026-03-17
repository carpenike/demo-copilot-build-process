"""Feedback and FeedbackFlag ORM models for quality tracking."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.document import Base


class Feedback(Base):
    """Employee feedback on a chatbot response — thumbs up/down with optional comment."""

    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[str] = mapped_column(
        Enum("positive", "negative", name="rating_enum", create_constraint=True),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FeedbackFlag(Base):
    """Aggregation record for topics that received repeated negative feedback."""

    __tablename__ = "feedback_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    negative_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        Enum(
            "flagged",
            "reviewed",
            "resolved",
            name="flag_status_enum",
            create_constraint=True,
        ),
        default="flagged",
        server_default="flagged",
    )
    first_flagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
