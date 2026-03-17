"""Shared test fixtures for the policy chatbot test suite.

Provides a configured FastAPI test client with all external services
mocked (Azure OpenAI, AI Search, Blob Storage, PostgreSQL, Redis).
No real Azure credentials or infrastructure are needed to run tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Set required env vars BEFORE any import of app code triggers Settings()
_ENV_VARS = {
    "POLICY_CHATBOT_DATABASE_URL": "postgresql+asyncpg://test:test@localhost/testdb",
    "POLICY_CHATBOT_REDIS_URL": "redis://localhost:6379/0",
    "POLICY_CHATBOT_AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
    "POLICY_CHATBOT_AZURE_SEARCH_ENDPOINT": "https://test.search.windows.net",
    "POLICY_CHATBOT_AZURE_STORAGE_ACCOUNT_URL": "https://test.blob.core.windows.net",
    "POLICY_CHATBOT_AZURE_TENANT_ID": "test-tenant-id",
    "POLICY_CHATBOT_AZURE_CLIENT_ID": "test-client-id",
    "POLICY_CHATBOT_DEBUG": "true",
}


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set all required environment variables for every test."""
    for key, value in _ENV_VARS.items():
        monkeypatch.setenv(key, value)


# --- Mock services ---


def _make_mock_conversation() -> MagicMock:
    """Create a mock conversation object."""
    conv = MagicMock()
    conv.id = uuid.uuid4()
    conv.user_entra_id = "test-user-id"
    conv.user_display_name = "Test User"
    conv.channel = "webchat"
    conv.status = "active"
    conv.started_at = datetime.now(UTC)
    conv.last_activity_at = datetime.now(UTC)
    return conv


def _make_mock_message(
    role: str = "assistant", content: str = "Test answer"
) -> MagicMock:
    """Create a mock message object."""
    msg = MagicMock()
    msg.id = uuid.uuid4()
    msg.conversation_id = uuid.uuid4()
    msg.role = role
    msg.content = content
    msg.citations = None
    msg.checklist = None
    msg.intent_domain = "HR"
    msg.intent_type = "factual"
    msg.confidence_score = 0.9
    msg.escalated = False
    msg.created_at = datetime.now(UTC)
    return msg


def _make_mock_feedback() -> MagicMock:
    """Create a mock feedback object."""
    fb = MagicMock()
    fb.id = uuid.uuid4()
    fb.message_id = uuid.uuid4()
    fb.conversation_id = uuid.uuid4()
    fb.rating = "positive"
    fb.comment = None
    fb.created_at = datetime.now(UTC)
    return fb


@pytest.fixture()
def mock_conv_service() -> AsyncMock:
    """Mock ConversationService with default return values."""
    service = AsyncMock()
    service.get_or_create_conversation = AsyncMock(return_value=_make_mock_conversation())
    service.save_message = AsyncMock(return_value=_make_mock_message())
    service.get_conversation_context = AsyncMock(return_value=[])
    service.update_conversation_context = AsyncMock()
    service.increment_low_confidence_count = AsyncMock(return_value=1)
    service.reset_low_confidence_count = AsyncMock()
    service.mark_escalated = AsyncMock()
    service.get_transcript = AsyncMock(
        return_value=[{"role": "user", "content": "hello"}]
    )
    return service


@pytest.fixture()
def mock_llm_service() -> AsyncMock:
    """Mock LLMService with default return values."""
    service = AsyncMock()
    service.classify_intent = AsyncMock(
        return_value={"domain": "HR", "type": "factual", "reasoning": "test"}
    )
    service.generate_answer = AsyncMock(
        return_value={
            "answer": "The bereavement leave policy allows 5 days.",
            "citations": [
                {
                    "document_title": "Bereavement Leave Policy",
                    "section": "Section 3.2",
                    "effective_date": "2025-06-01",
                    "source_url": "https://intranet.acme.com/policies/hr/bereavement",
                }
            ],
            "checklist": None,
            "confidence": 0.92,
        }
    )
    service.generate_embedding = AsyncMock(return_value=[0.1] * 3072)
    service.check_health = AsyncMock(return_value=True)
    return service


@pytest.fixture()
def mock_search_service() -> AsyncMock:
    """Mock SearchService with default return values."""
    service = AsyncMock()
    service.hybrid_search = AsyncMock(
        return_value=[
            {
                "chunk_id": "chunk-1",
                "document_id": str(uuid.uuid4()),
                "content": "Bereavement leave is 5 days for immediate family.",
                "title": "Bereavement Leave Policy",
                "section_heading": "Section 3.2",
                "category": "HR",
                "effective_date": "2025-06-01",
                "source_url": "https://intranet.acme.com/policies/hr/bereavement",
                "page_number": 3,
                "score": 0.95,
                "reranker_score": 0.88,
            }
        ]
    )
    service.keyword_search = AsyncMock(
        return_value=[
            {
                "chunk_id": "chunk-1",
                "document_id": str(uuid.uuid4()),
                "content": "Bereavement leave is 5 days.",
                "title": "Bereavement Leave Policy",
                "section_heading": "Section 3.2",
                "source_url": "https://intranet.acme.com/policies/hr/bereavement",
            }
        ]
    )
    service.ensure_index = AsyncMock()
    service.check_health = AsyncMock(return_value=True)
    service.delete_document_chunks = AsyncMock()
    return service


@pytest.fixture()
def mock_doc_service() -> AsyncMock:
    """Mock DocumentService with default return values."""
    service = AsyncMock()
    service.list_documents = AsyncMock(return_value=([], None, 0))
    service.get_document_versions = AsyncMock(return_value=[])
    service.get_coverage = AsyncMock(
        return_value=[
            {"name": "HR", "document_count": 42, "status": "covered"},
            {"name": "IT", "document_count": 28, "status": "covered"},
            {"name": "Finance", "document_count": 18, "status": "covered"},
            {"name": "Facilities", "document_count": 22, "status": "covered"},
            {"name": "Legal", "document_count": 15, "status": "covered"},
            {"name": "Compliance", "document_count": 12, "status": "covered"},
            {"name": "Safety", "document_count": 5, "status": "covered"},
        ]
    )
    service.retire_document = AsyncMock()
    service.upload_document = AsyncMock()
    return service


@pytest.fixture()
def mock_feedback_service() -> AsyncMock:
    """Mock FeedbackService with default return values."""
    service = AsyncMock()
    service.submit_feedback = AsyncMock(return_value=_make_mock_feedback())
    service.record_analytics_event = AsyncMock()
    service.get_analytics = AsyncMock(
        return_value={
            "total_queries": 100,
            "resolution_rate": 0.78,
            "escalation_rate": 0.12,
            "average_satisfaction": 4.2,
            "unanswered_count": 5,
        }
    )
    service.get_top_intents = AsyncMock(return_value=[])
    service.get_flagged_topics = AsyncMock(return_value=[])
    return service


@pytest.fixture()
def mock_db() -> AsyncMock:
    """Mock async database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture()
def mock_redis() -> AsyncMock:
    """Mock async Redis client."""
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    return redis


@pytest.fixture()
def app(
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    mock_conv_service: AsyncMock,
    mock_llm_service: AsyncMock,
    mock_search_service: AsyncMock,
    mock_doc_service: AsyncMock,
    mock_feedback_service: AsyncMock,
) -> FastAPI:
    """Create a FastAPI app with all dependencies mocked.

    Bypasses the lifespan context manager entirely — services are injected
    directly onto app.state so no Azure credentials are needed.
    """
    from app.api.dependencies import (
        get_conversation_service,
        get_current_user,
        get_db,
        get_document_service,
        get_feedback_service,
        get_llm_service,
        get_redis,
        get_search_service,
        get_settings,
        require_admin,
    )
    from app.config import Settings

    test_app = FastAPI()

    # Import and register routers
    from app.api.admin import router as admin_router
    from app.api.chat import router as chat_router
    from app.api.health import router as health_router

    test_app.include_router(health_router)
    test_app.include_router(chat_router)
    test_app.include_router(admin_router)

    settings = Settings()
    test_app.state.settings = settings
    test_app.state.async_session = MagicMock(return_value=AsyncMock())

    # Override all dependencies
    async def _db_override() -> Any:
        yield mock_db

    test_app.dependency_overrides[get_db] = _db_override
    test_app.dependency_overrides[get_redis] = lambda: mock_redis
    test_app.dependency_overrides[get_settings] = lambda: settings
    test_app.dependency_overrides[get_search_service] = lambda: mock_search_service
    test_app.dependency_overrides[get_llm_service] = lambda: mock_llm_service
    test_app.dependency_overrides[get_document_service] = lambda: mock_doc_service
    test_app.dependency_overrides[get_conversation_service] = lambda: mock_conv_service
    test_app.dependency_overrides[get_feedback_service] = lambda: mock_feedback_service

    return test_app


@pytest.fixture()
def authed_app(app: FastAPI) -> FastAPI:
    """App with auth overridden to return an authenticated employee user."""
    from app.api.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "test-user-id",
        "name": "Test User",
        "preferred_username": "test@acme.com",
        "roles": ["Employee"],
    }
    return app


@pytest.fixture()
def admin_app(app: FastAPI) -> FastAPI:
    """App with auth overridden to return an authenticated admin user."""
    from app.api.dependencies import get_current_user, require_admin

    admin_user = {
        "sub": "admin-user-id",
        "name": "Admin User",
        "preferred_username": "admin@acme.com",
        "roles": ["Employee", "PolicyAdmin"],
    }
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[require_admin] = lambda: admin_user
    return app


@pytest.fixture()
def client(authed_app: FastAPI) -> TestClient:
    """Test client with employee auth."""
    return TestClient(authed_app)


@pytest.fixture()
def admin_client(admin_app: FastAPI) -> TestClient:
    """Test client with admin auth."""
    return TestClient(admin_app)


@pytest.fixture()
def unauthed_client(app: FastAPI) -> TestClient:
    """Test client with NO auth override (uses real dependency)."""
    # Remove any auth override so the real get_current_user runs
    from app.api.dependencies import get_current_user

    app.dependency_overrides.pop(get_current_user, None)
    # Set debug=False so auth is enforced
    app.state.settings.debug = False
    return TestClient(app)
