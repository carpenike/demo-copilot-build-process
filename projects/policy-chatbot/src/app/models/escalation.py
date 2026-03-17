"""Escalation ORM model for conversations handed off to a live agent."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.document import Base


class Escalation(Base):
    """Records a conversation escalation to the service desk via ServiceNow."""

    __tablename__ = "escalations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    target_team: Mapped[str] = mapped_column(String(50), nullable=False)
    servicenow_ticket_id: Mapped[str | None] = mapped_column(String(100))
    transcript_summary: Mapped[str | None] = mapped_column(Text)
    identified_intent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
