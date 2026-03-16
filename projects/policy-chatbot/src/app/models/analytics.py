"""Analytics event ORM model for tracking chatbot usage metrics."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.document import Base


class AnalyticsEvent(Base):
    """Individual analytics event for dashboard aggregation."""

    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column()
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    intent: Mapped[str | None] = mapped_column(String(255))
    policy_domain: Mapped[str | None] = mapped_column(String(50))
    resolved: Mapped[bool | None] = mapped_column(Boolean)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
