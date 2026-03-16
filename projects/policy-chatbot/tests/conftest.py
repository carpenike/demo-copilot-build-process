"""Shared test fixtures for the Policy Chatbot test suite."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    AuthenticatedUser,
    get_blob_service,
    get_current_user,
    get_db,
    get_graph_service,
    get_openai_service,
    get_rag_pipeline,
    get_redis,
    get_search_service,
    get_servicenow_service,
    require_admin,
)
from app.core.rag_pipeline import RAGPipeline
from app.services.blob_service import BlobService
from app.services.graph_service import GraphService
from app.services.openai_service import OpenAIService
from app.services.redis_service import RedisService
from app.services.search_service import SearchService
from app.services.servicenow_service import ServiceNowService


# --- Fake users ---


def make_employee_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="user-emp-001",
        roles=["Employee"],
        name="Alex Johnson",
    )


def make_admin_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="user-admin-001",
        roles=["Administrator", "Employee"],
        name="Policy Admin",
    )


# --- Mock services ---


@pytest.fixture()
def mock_db() -> AsyncMock:
    """Mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture()
def mock_redis() -> AsyncMock:
    """Mock Redis service."""
    redis = AsyncMock(spec=RedisService)
    redis.get_user_session.return_value = {
        "display_name": "Alex Johnson",
        "department": "Engineering",
        "location": "HQ - Building A",
        "role": "Employee",
    }
    redis.get_conversation_history.return_value = []
    redis.check_rate_limit.return_value = True
    redis.get_cached_response.return_value = None
    redis.is_available.return_value = True
    return redis


@pytest.fixture()
def mock_search() -> AsyncMock:
    """Mock Azure AI Search service."""
    return AsyncMock(spec=SearchService)


@pytest.fixture()
def mock_openai() -> AsyncMock:
    """Mock Azure OpenAI service."""
    openai = AsyncMock(spec=OpenAIService)
    openai.is_available.return_value = True
    openai.generate_embedding.return_value = [0.1] * 1536
    return openai


@pytest.fixture()
def mock_blob() -> AsyncMock:
    """Mock Azure Blob Storage service."""
    return AsyncMock(spec=BlobService)


@pytest.fixture()
def mock_servicenow() -> AsyncMock:
    """Mock ServiceNow service."""
    servicenow = AsyncMock(spec=ServiceNowService)
    servicenow.create_escalation_ticket.return_value = "INC0012345"
    return servicenow


@pytest.fixture()
def mock_graph() -> AsyncMock:
    """Mock Microsoft Graph API service."""
    graph = AsyncMock(spec=GraphService)
    graph.get_user_profile.return_value = {
        "display_name": "Alex Johnson",
        "department": "Engineering",
        "location": "HQ - Building A",
        "role": "Employee",
    }
    return graph


@pytest.fixture()
def mock_rag_pipeline(
    mock_search: AsyncMock,
    mock_openai: AsyncMock,
    mock_redis: AsyncMock,
) -> RAGPipeline:
    """RAG pipeline with mocked dependencies."""
    return RAGPipeline(
        search_service=mock_search,
        openai_service=mock_openai,
        redis_service=mock_redis,
    )


# --- FastAPI test clients ---


def _create_test_client(
    *,
    user: AuthenticatedUser | None = None,
    admin_user: AuthenticatedUser | None = None,
    mock_db_session: AsyncMock | None = None,
    redis: AsyncMock | None = None,
    search: AsyncMock | None = None,
    openai: AsyncMock | None = None,
    blob: AsyncMock | None = None,
    servicenow: AsyncMock | None = None,
    graph: AsyncMock | None = None,
    rag: RAGPipeline | None = None,
) -> TestClient:
    """Create a FastAPI TestClient with dependency overrides."""
    from app.main import create_app

    app = create_app()

    if user:
        app.dependency_overrides[get_current_user] = lambda: user
    if admin_user:
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[require_admin] = lambda: admin_user
    if mock_db_session:

        async def _db_override() -> AsyncGenerator:
            yield mock_db_session

        app.dependency_overrides[get_db] = _db_override
    if redis:
        app.dependency_overrides[get_redis] = lambda: redis
    if search:
        app.dependency_overrides[get_search_service] = lambda: search
    if openai:
        app.dependency_overrides[get_openai_service] = lambda: openai
    if blob:
        app.dependency_overrides[get_blob_service] = lambda: blob
    if servicenow:
        app.dependency_overrides[get_servicenow_service] = lambda: servicenow
    if graph:
        app.dependency_overrides[get_graph_service] = lambda: graph
    if rag:
        app.dependency_overrides[get_rag_pipeline] = lambda: rag

    return TestClient(app)


@pytest.fixture()
def employee_client(
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    mock_search: AsyncMock,
    mock_openai: AsyncMock,
    mock_blob: AsyncMock,
    mock_servicenow: AsyncMock,
    mock_graph: AsyncMock,
    mock_rag_pipeline: RAGPipeline,
) -> TestClient:
    """TestClient authenticated as an Employee."""
    return _create_test_client(
        user=make_employee_user(),
        mock_db_session=mock_db,
        redis=mock_redis,
        search=mock_search,
        openai=mock_openai,
        blob=mock_blob,
        servicenow=mock_servicenow,
        graph=mock_graph,
        rag=mock_rag_pipeline,
    )


@pytest.fixture()
def admin_client(
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    mock_search: AsyncMock,
    mock_openai: AsyncMock,
    mock_blob: AsyncMock,
    mock_servicenow: AsyncMock,
    mock_graph: AsyncMock,
    mock_rag_pipeline: RAGPipeline,
) -> TestClient:
    """TestClient authenticated as an Administrator."""
    return _create_test_client(
        admin_user=make_admin_user(),
        mock_db_session=mock_db,
        redis=mock_redis,
        search=mock_search,
        openai=mock_openai,
        blob=mock_blob,
        servicenow=mock_servicenow,
        graph=mock_graph,
        rag=mock_rag_pipeline,
    )


@pytest.fixture()
def unauthenticated_client() -> TestClient:
    """TestClient with no authentication — should get 401 on protected endpoints."""
    from app.main import create_app

    app = create_app()
    return TestClient(app)
