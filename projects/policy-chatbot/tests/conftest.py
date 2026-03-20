"""Shared test fixtures for the Policy Chatbot test suite."""

import uuid
from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser


def _populate_orm_defaults(obj: Any) -> None:
    """Simulate SQLAlchemy default population on db.add for ORM objects."""
    if hasattr(obj, "id") and getattr(obj, "id", None) is None:
        obj.id = uuid.uuid4()
    if hasattr(obj, "status") and getattr(obj, "status", None) is None:
        obj.status = "active"
    if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
        obj.created_at = datetime.now(UTC)
    if hasattr(obj, "updated_at") and getattr(obj, "updated_at", None) is None:
        obj.updated_at = datetime.now(UTC)
    if hasattr(obj, "message_count") and getattr(obj, "message_count", None) is None:
        obj.message_count = 0
    if hasattr(obj, "started_at") and getattr(obj, "started_at", None) is None:
        obj.started_at = datetime.now(UTC)


# ---------------------------------------------------------------------------
# User Factories
# ---------------------------------------------------------------------------

def make_employee_user(**overrides: Any) -> CurrentUser:
    """Create a CurrentUser with Employee role."""
    defaults = {
        "user_id": str(uuid.uuid4()),
        "email": "employee@acme.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "roles": ["Employee"],
    }
    defaults.update(overrides)
    return CurrentUser(**defaults)


def make_admin_user(**overrides: Any) -> CurrentUser:
    """Create a CurrentUser with Admin role."""
    defaults = {
        "user_id": str(uuid.uuid4()),
        "email": "admin@acme.com",
        "first_name": "Admin",
        "last_name": "User",
        "roles": ["Admin"],
    }
    defaults.update(overrides)
    return CurrentUser(**defaults)


# ---------------------------------------------------------------------------
# DB Model Factories
# ---------------------------------------------------------------------------

def make_user_record(**overrides: Any) -> MagicMock:
    """Create a User DB record mock."""
    defaults = {
        "id": uuid.uuid4(),
        "email": "employee@acme.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "department": "Engineering",
        "location": "HQ Campus",
        "role": "Employee",
        "manager_email": "manager@acme.com",
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_conversation(**overrides: Any) -> MagicMock:
    """Create a Conversation DB record mock."""
    defaults = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "started_at": datetime.now(UTC),
        "last_message_at": datetime.now(UTC),
        "message_count": 2,
        "status": "active",
        "escalation_ticket_id": None,
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_message(**overrides: Any) -> MagicMock:
    """Create a Message DB record mock."""
    defaults = {
        "id": uuid.uuid4(),
        "conversation_id": uuid.uuid4(),
        "role": "assistant",
        "content": "Based on the policy...",
        "citations": None,
        "intent": None,
        "response_type": "answer",
        "checklist": None,
        "wayfinding": None,
        "token_count": None,
        "response_time_ms": None,
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_document(**overrides: Any) -> MagicMock:
    """Create a Document DB record mock."""
    defaults = {
        "id": uuid.uuid4(),
        "title": "HR-POL-042: Bereavement Leave Policy",
        "category": "HR",
        "status": "active",
        "effective_date": date(2025, 9, 1),
        "review_date": date(2026, 9, 1),
        "owner": "Jane Smith",
        "source_url": "https://intranet.acme.com/policies/HR-POL-042",
        "current_version": 1,
        "last_indexed_at": datetime.now(UTC),
        "page_count": 12,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_document_version(**overrides: Any) -> MagicMock:
    """Create a DocumentVersion DB record mock."""
    defaults = {
        "id": uuid.uuid4(),
        "document_id": uuid.uuid4(),
        "version_number": 1,
        "blob_path": "HR/doc-id/1.pdf",
        "file_type": "pdf",
        "file_size_bytes": 1024,
        "is_active": True,
        "uploaded_by": "admin@acme.com",
        "uploaded_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def make_feedback(**overrides: Any) -> MagicMock:
    """Create a Feedback DB record mock."""
    defaults = {
        "id": uuid.uuid4(),
        "message_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "rating": "positive",
        "comment": None,
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


# ---------------------------------------------------------------------------
# Mock DB Session
# ---------------------------------------------------------------------------

def make_mock_db() -> AsyncMock:
    """Create a mock AsyncSession that populates ORM defaults on add."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock(side_effect=_populate_orm_defaults)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.delete = AsyncMock()
    return db


def mock_db_scalar_result(value: Any) -> MagicMock:
    """Create a mock execute result that returns a scalar.

    Uses MagicMock (not AsyncMock) because SQLAlchemy Result methods like
    scalar_one_or_none() and scalars() are synchronous.
    """
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = value
    mock_result.scalars.return_value.all.return_value = (
        value if isinstance(value, list) else [value] if value else []
    )
    mock_result.scalar.return_value = value
    mock_result.one.return_value = value
    mock_result.all.return_value = value if isinstance(value, list) else [value] if value else []
    return mock_result


# ---------------------------------------------------------------------------
# Mock Service Factories
# ---------------------------------------------------------------------------

def make_mock_services() -> dict[str, AsyncMock]:
    """Create all mock service instances used by the app."""
    search = AsyncMock()
    search.hybrid_search.return_value = []
    search.ensure_index = AsyncMock()
    search.reindex_document = AsyncMock()
    search.reindex_all = AsyncMock(return_value=0)
    search.check_health = AsyncMock(return_value=True)

    openai = AsyncMock()
    openai.classify_intent.return_value = {
        "type": "factual",
        "domain": "HR",
        "confidence": 0.85,
    }
    openai.generate_answer.return_value = {
        "content": "Based on the policy...",
        "citations": [],
        "response_type": "answer",
    }
    openai.check_health = AsyncMock(return_value=True)

    redis = AsyncMock()
    redis.get_session.return_value = None
    redis.set_session = AsyncMock()
    redis.check_health = AsyncMock(return_value=True)

    blob = AsyncMock()
    blob.upload = AsyncMock(return_value="path/to/blob")
    blob.check_health = AsyncMock(return_value=True)

    servicenow = AsyncMock()
    servicenow.create_incident = AsyncMock(return_value="INC0000001")

    graph = AsyncMock()
    graph.get_user_profile.return_value = {
        "email": "user@acme.com",
        "first_name": "Demo",
        "last_name": "User",
    }

    return {
        "search_service": search,
        "openai_service": openai,
        "redis_service": redis,
        "blob_service": blob,
        "servicenow_client": servicenow,
        "graph_service": graph,
    }


# ---------------------------------------------------------------------------
# App Builder for Integration Tests
# ---------------------------------------------------------------------------

def build_test_app(
    router: Any,
    current_user: CurrentUser | None = None,
    mock_db: AsyncMock | None = None,
    services: dict[str, AsyncMock] | None = None,
    *,
    admin_required: bool = False,
) -> Any:
    """Build a minimal FastAPI app with mocked dependencies for testing."""
    from fastapi import FastAPI

    from app.core.auth import get_current_user as _get_current_user
    from app.core.auth import require_admin as _require_admin

    app = FastAPI()
    app.include_router(router)

    if current_user is not None:
        app.dependency_overrides[_get_current_user] = lambda: current_user
        if admin_required or current_user.is_admin:
            app.dependency_overrides[_require_admin] = lambda: current_user

    if mock_db is not None:

        async def _override_db() -> Any:
            yield mock_db

        from app.api.chat import _get_db

        app.dependency_overrides[_get_db] = _override_db

    # Attach mock services to app state
    if services:
        for attr, svc in services.items():
            setattr(app.state, attr, svc)

    # Attach a mock db_session_factory for readiness checks
    if mock_db is not None:
        app.state.db_session_factory = AsyncMock()

    return app


async def make_async_client(app: Any) -> AsyncClient:
    """Create an httpx AsyncClient bound to the test app."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
