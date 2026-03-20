"""Integration tests for admin analytics endpoints.

Covers: FR-029, FR-030
User Stories: US-010
"""

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.analytics import router
from conftest import (
    build_test_app,
    make_admin_user,
    make_employee_user,
    make_mock_db,
    make_mock_services,
    mock_db_scalar_result,
)


def _build_analytics_app(user=None, db=None):
    user = user or make_admin_user()
    db = db or make_mock_db()
    return build_test_app(
        router, current_user=user, mock_db=db, admin_required=True
    )


def _make_analytics_daily(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "date": date(2026, 3, 15),
        "total_queries": 200,
        "resolved_queries": 170,
        "escalated_queries": 15,
        "no_match_queries": 10,
        "positive_feedback_count": 80,
        "negative_feedback_count": 20,
        "avg_response_time_ms": 1200.0,
        "computed_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_intent_count(**overrides):
    defaults = {
        "intent_label": "PTO policy",
        "domain": "HR",
        "count": 87,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_unanswered(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "query_text": "What's the policy on bringing dogs?",
        "detected_intent": "pet policy",
        "detected_domain": "Facilities",
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_flagged_topic(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "topic": "Remote work — equipment reimbursement",
        "domain": "IT",
        "negative_count": 7,
        "sample_comments": ["Outdated", "Wrong amount"],
        "first_flagged_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


# ---------------------------------------------------------------------------
# IT-ANA-001: GET /v1/admin/analytics/summary (FR-029)
# ---------------------------------------------------------------------------


class TestAnalyticsSummary:
    """GET /v1/admin/analytics/summary returns dashboard metrics."""

    @pytest.mark.asyncio
    async def test_summary_returns_metrics(self) -> None:
        """IT-ANA-001: Summary response includes all required fields."""
        db = make_mock_db()
        row = _make_analytics_daily()

        result = AsyncMock()
        result.scalars.return_value.all.return_value = [row]
        db.execute.return_value = result

        app = _build_analytics_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/admin/analytics/summary?period=7d")

        assert response.status_code == 200
        data = response.json()
        assert "total_queries" in data
        assert "resolution_rate" in data
        assert "escalation_rate" in data
        assert "average_satisfaction" in data
        assert "daily_volumes" in data
        assert data["period"] == "7d"

    @pytest.mark.asyncio
    async def test_summary_empty_period(self) -> None:
        """IT-ANA-001b: No data for period returns zeroes."""
        db = make_mock_db()

        result = AsyncMock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result

        app = _build_analytics_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/admin/analytics/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_queries"] == 0

    @pytest.mark.asyncio
    async def test_summary_employee_forbidden(self) -> None:
        """SEC-006: Employee accessing analytics returns 403."""
        employee = make_employee_user()
        db = make_mock_db()
        app = build_test_app(router, current_user=employee, mock_db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/admin/analytics/summary")

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# IT-ANA-002: GET /v1/admin/analytics/top-intents (FR-029)
# ---------------------------------------------------------------------------


class TestTopIntents:
    """GET /v1/admin/analytics/top-intents returns frequent intents."""

    @pytest.mark.asyncio
    async def test_top_intents_returns_data(self) -> None:
        """IT-ANA-002: Returns list of intents with counts."""
        db = make_mock_db()

        # Returns rows as tuples: (intent_label, domain, total)
        result = AsyncMock()
        result.all.return_value = [
            ("PTO policy", "HR", 87),
            ("Parking badge", "Facilities", 63),
        ]
        db.execute.return_value = result

        app = _build_analytics_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/admin/analytics/top-intents")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2
        assert data["data"][0]["intent"] == "PTO policy"


# ---------------------------------------------------------------------------
# IT-ANA-003: GET /v1/admin/analytics/unanswered (FR-029)
# ---------------------------------------------------------------------------


class TestUnansweredQueries:
    """GET /v1/admin/analytics/unanswered returns unmatched query log."""

    @pytest.mark.asyncio
    async def test_unanswered_returns_data(self) -> None:
        """IT-ANA-003: Returns list of unmatched queries."""
        db = make_mock_db()
        unanswered = _make_unanswered()

        result = AsyncMock()
        result.scalars.return_value.all.return_value = [unanswered]
        db.execute.return_value = result

        app = _build_analytics_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/admin/analytics/unanswered")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["query_text"] == "What's the policy on bringing dogs?"


# ---------------------------------------------------------------------------
# IT-ANA-004: GET /v1/admin/analytics/flagged-topics (FR-030)
# ---------------------------------------------------------------------------


class TestFlaggedTopics:
    """GET /v1/admin/analytics/flagged-topics returns negatively-flagged topics."""

    @pytest.mark.asyncio
    async def test_flagged_topics_returns_data(self) -> None:
        """IT-ANA-004: Returns list of flagged topics with counts."""
        db = make_mock_db()
        topic = _make_flagged_topic()

        result = AsyncMock()
        result.scalars.return_value.all.return_value = [topic]
        db.execute.return_value = result

        app = _build_analytics_app(db=db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/admin/analytics/flagged-topics")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["negative_count"] == 7
