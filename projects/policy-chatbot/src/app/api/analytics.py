"""Analytics endpoints — summary, top intents, unanswered, flagged topics."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.chat import _get_db
from app.core.auth import CurrentUser, require_admin
from app.models.database import (
    AnalyticsDaily,
    FlaggedTopic,
    IntentCount,
    UnansweredQuery,
)
from app.models.schemas import (
    AnalyticsSummaryResponse,
    DailyVolume,
    FlaggedTopicItem,
    FlaggedTopicsResponse,
    IntentStat,
    TopIntentsResponse,
    UnansweredItem,
    UnansweredResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/admin/analytics", tags=["analytics"])

_PERIOD_DAYS = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}


def _resolve_period(period: str) -> tuple[str, date]:
    """Convert period string to (label, start_date)."""
    days = _PERIOD_DAYS.get(period)
    if days is None:
        days = 7
        period = "7d"
    start = date.today() - timedelta(days=days)
    return period, start


# ---------------------------------------------------------------------------
# GET /v1/admin/analytics/summary
# ---------------------------------------------------------------------------
@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def analytics_summary(
    period: str = "7d",
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Retrieve dashboard summary metrics."""
    label, start_date = _resolve_period(period)

    result = await db.execute(
        select(AnalyticsDaily)
        .where(AnalyticsDaily.date >= start_date)
        .order_by(AnalyticsDaily.date.asc())
    )
    rows = list(result.scalars().all())

    total_queries = sum(r.total_queries for r in rows)
    resolved = sum(r.resolved_queries for r in rows)
    escalated = sum(r.escalated_queries for r in rows)
    no_match = sum(r.no_match_queries for r in rows)
    pos = sum(r.positive_feedback_count for r in rows)
    neg = sum(r.negative_feedback_count for r in rows)

    resolution_rate = resolved / total_queries if total_queries else 0.0
    escalation_rate = escalated / total_queries if total_queries else 0.0
    no_match_rate = no_match / total_queries if total_queries else 0.0
    total_feedback = pos + neg
    avg_satisfaction = (pos / total_feedback * 5.0) if total_feedback else 0.0

    return AnalyticsSummaryResponse(
        period=label,
        total_queries=total_queries,
        resolution_rate=round(resolution_rate, 2),
        escalation_rate=round(escalation_rate, 2),
        average_satisfaction=round(avg_satisfaction, 1),
        no_match_rate=round(no_match_rate, 2),
        daily_volumes=[DailyVolume(date=r.date, count=r.total_queries) for r in rows],
    )


# ---------------------------------------------------------------------------
# GET /v1/admin/analytics/top-intents
# ---------------------------------------------------------------------------
@router.get("/top-intents", response_model=TopIntentsResponse)
async def top_intents(
    period: str = "7d",
    limit: int = 20,
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Retrieve the top N most frequent intents."""
    limit = min(limit, 50)
    _, start_date = _resolve_period(period)

    result = await db.execute(
        select(
            IntentCount.intent_label,
            IntentCount.domain,
            func.sum(IntentCount.count).label("total"),
        )
        .where(IntentCount.date >= start_date)
        .group_by(IntentCount.intent_label, IntentCount.domain)
        .order_by(func.sum(IntentCount.count).desc())
        .limit(limit)
    )
    rows = result.all()

    return TopIntentsResponse(
        data=[
            IntentStat(
                intent=r[0],
                domain=r[1],
                count=r[2],
                resolution_rate=0.0,  # computed from message-level data in production
            )
            for r in rows
        ]
    )


# ---------------------------------------------------------------------------
# GET /v1/admin/analytics/unanswered
# ---------------------------------------------------------------------------
@router.get("/unanswered", response_model=UnansweredResponse)
async def unanswered_queries(
    cursor: str | None = None,
    limit: int = 20,
    period: str = "7d",
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Retrieve log of queries that could not be matched to a policy."""
    limit = min(limit, 100)
    _, start_date = _resolve_period(period)

    query = (
        select(UnansweredQuery)
        .where(
            UnansweredQuery.created_at
            >= datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        )
        .order_by(UnansweredQuery.created_at.desc())
        .limit(limit + 1)
    )
    if cursor:
        try:
            cursor_id = uuid.UUID(cursor)
            query = query.where(UnansweredQuery.id < cursor_id)
        except ValueError:
            pass

    result = await db.execute(query)
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    return UnansweredResponse(
        data=[
            UnansweredItem(
                id=r.id,
                query_text=r.query_text,
                detected_intent=r.detected_intent,
                detected_domain=r.detected_domain,
                timestamp=r.created_at,
            )
            for r in rows
        ],
        next_cursor=str(rows[-1].id) if has_more else None,
    )


# ---------------------------------------------------------------------------
# GET /v1/admin/analytics/flagged-topics
# ---------------------------------------------------------------------------
@router.get("/flagged-topics", response_model=FlaggedTopicsResponse)
async def flagged_topics(
    cursor: str | None = None,
    limit: int = 20,
    _admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(_get_db),
) -> Any:
    """Retrieve topics flagged due to repeated negative feedback."""
    limit = min(limit, 100)

    query = select(FlaggedTopic).order_by(FlaggedTopic.negative_count.desc()).limit(limit + 1)
    if cursor:
        try:
            cursor_id = uuid.UUID(cursor)
            query = query.where(FlaggedTopic.id < cursor_id)
        except ValueError:
            pass

    result = await db.execute(query)
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    return FlaggedTopicsResponse(
        data=[
            FlaggedTopicItem(
                topic=r.topic,
                domain=r.domain,
                negative_count=r.negative_count,
                sample_comments=r.sample_comments or [],
                first_flagged_at=r.first_flagged_at,
            )
            for r in rows
        ],
        next_cursor=str(rows[-1].id) if has_more else None,
    )
