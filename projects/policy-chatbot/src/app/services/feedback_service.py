"""Feedback service for recording and analyzing employee feedback.

Handles feedback submission, duplicate detection, and flagging of
topics with repeated negative feedback (FR-028, FR-030).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AnalyticsEvent, Feedback, Message

if TYPE_CHECKING:
    from app.config import Settings

logger = structlog.get_logger()


class FeedbackService:
    """Records feedback and generates analytics for the admin dashboard."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def submit_feedback(
        self,
        db: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        message_id: uuid.UUID,
        rating: str,
        comment: str | None,
        user_entra_id: str,
    ) -> Feedback:
        """Record feedback on a specific assistant message."""
        result = await db.execute(
            select(Message).where(
                Message.id == message_id,
                Message.conversation_id == conversation_id,
            )
        )
        message = result.scalar_one()

        if message.role != "assistant":
            msg = "Feedback can only be submitted on assistant messages"
            raise ValueError(msg)

        existing = await db.execute(select(Feedback).where(Feedback.message_id == message_id))
        if existing.scalar_one_or_none():
            msg = "Feedback already submitted for this message"
            raise ValueError(msg)

        feedback = Feedback(
            message_id=message_id,
            conversation_id=conversation_id,
            rating=rating,
            comment=comment,
        )
        db.add(feedback)

        event = AnalyticsEvent(
            event_type="feedback",
            conversation_id=conversation_id,
            intent_domain=message.intent_domain,
            metadata_={"rating": rating, "has_comment": comment is not None},
            event_date=date.today(),
        )
        db.add(event)

        await db.commit()
        await db.refresh(feedback)

        logger.info(
            "feedback_submitted",
            feedback_id=str(feedback.id),
            rating=rating,
        )
        return feedback

    async def get_analytics(
        self,
        db: AsyncSession,
        *,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Aggregate analytics data for the admin dashboard."""
        query_events = await db.execute(
            select(func.count()).where(
                AnalyticsEvent.event_type == "query",
                AnalyticsEvent.event_date >= start_date,
                AnalyticsEvent.event_date <= end_date,
            )
        )
        total_queries = query_events.scalar() or 0

        escalation_events = await db.execute(
            select(func.count()).where(
                AnalyticsEvent.event_type == "escalation",
                AnalyticsEvent.event_date >= start_date,
                AnalyticsEvent.event_date <= end_date,
            )
        )
        total_escalations = escalation_events.scalar() or 0

        escalation_rate = total_escalations / total_queries if total_queries > 0 else 0.0
        resolution_rate = 1.0 - escalation_rate

        positive_feedback = await db.execute(
            select(func.count()).where(
                Feedback.rating == "positive",
                Feedback.created_at >= start_date.isoformat(),
            )
        )
        negative_feedback = await db.execute(
            select(func.count()).where(
                Feedback.rating == "negative",
                Feedback.created_at >= start_date.isoformat(),
            )
        )
        pos_count = positive_feedback.scalar() or 0
        neg_count = negative_feedback.scalar() or 0
        total_feedback = pos_count + neg_count
        avg_satisfaction = (pos_count / total_feedback * 5.0) if total_feedback > 0 else 0.0

        return {
            "total_queries": total_queries,
            "resolution_rate": round(resolution_rate, 2),
            "escalation_rate": round(escalation_rate, 2),
            "average_satisfaction": round(avg_satisfaction, 1),
            "unanswered_count": 0,
        }

    async def get_top_intents(
        self,
        db: AsyncSession,
        *,
        start_date: date,
        end_date: date,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get the most frequently asked intents."""
        result = await db.execute(
            select(
                AnalyticsEvent.intent_domain,
                func.count().label("count"),
            )
            .where(
                AnalyticsEvent.event_type == "query",
                AnalyticsEvent.event_date >= start_date,
                AnalyticsEvent.event_date <= end_date,
                AnalyticsEvent.intent_domain.is_not(None),
            )
            .group_by(AnalyticsEvent.intent_domain)
            .order_by(func.count().desc())
            .limit(limit)
        )

        return [{"intent": row[0], "count": row[1]} for row in result.all()]

    async def get_flagged_topics(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Get topics with 3+ negative feedback entries for admin review (FR-030)."""
        result = await db.execute(
            select(
                Message.intent_domain,
                func.count().label("neg_count"),
            )
            .join(Feedback, Feedback.message_id == Message.id)
            .where(Feedback.rating == "negative")
            .group_by(Message.intent_domain)
            .having(func.count() >= 3)
            .order_by(func.count().desc())
        )

        flagged: list[dict[str, Any]] = []
        for row in result.all():
            domain = row[0] or "Unknown"
            neg_count = row[1]

            samples = await db.execute(
                select(Message.content, Feedback.comment)
                .join(Feedback, Feedback.message_id == Message.id)
                .where(
                    Message.intent_domain == row[0],
                    Feedback.rating == "negative",
                )
                .limit(3)
            )
            sample_rows = samples.all()

            flagged.append(
                {
                    "topic": domain,
                    "negative_feedback_count": neg_count,
                    "sample_queries": [r[0] for r in sample_rows if r[0]],
                    "sample_comments": [r[1] for r in sample_rows if r[1]],
                }
            )

        return flagged

    async def record_analytics_event(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        conversation_id: uuid.UUID | None = None,
        document_id: uuid.UUID | None = None,
        intent_domain: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a generic analytics event."""
        event = AnalyticsEvent(
            event_type=event_type,
            conversation_id=conversation_id,
            document_id=document_id,
            intent_domain=intent_domain,
            metadata_=metadata,
            event_date=date.today(),
        )
        db.add(event)
        await db.flush()
