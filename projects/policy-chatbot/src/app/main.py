"""FastAPI application factory.

Creates the FastAPI app with lifespan context manager for startup/shutdown.
All service initialization happens here — nothing at module scope.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and tear down application resources.

    Startup: create DB engine, Redis connection, service instances, AI Search index.
    Shutdown: close connections cleanly.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import Settings
    from app.services.conversation_service import ConversationService
    from app.services.document_service import DocumentService
    from app.services.feedback_service import FeedbackService
    from app.services.llm_service import LLMService
    from app.services.search_service import SearchService

    settings = Settings()
    app.state.settings = settings

    # Configure structured logging
    log_level: int = structlog.get_level_from_name(settings.log_level)  # type: ignore[operator]
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )

    # Configure OpenTelemetry with Azure Monitor
    if settings.applicationinsights_connection_string:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(
            connection_string=settings.applicationinsights_connection_string,
        )

    # Database engine
    engine = create_async_engine(settings.database_url, echo=settings.debug)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    app.state.async_session = async_session

    # Redis
    import redis.asyncio as aioredis

    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
    app.state.redis = redis_client

    # Services — initialized once, shared across requests via app.state
    search_service = SearchService(settings)
    llm_service = LLMService(settings)
    doc_service = DocumentService(settings)
    conv_service = ConversationService(settings, redis_client)
    feedback_service = FeedbackService(settings)

    app.state.search_service = search_service
    app.state.llm_service = llm_service
    app.state.document_service = doc_service
    app.state.conversation_service = conv_service
    app.state.feedback_service = feedback_service

    # Ensure AI Search index exists on startup
    try:
        await search_service.ensure_index()
    except Exception:
        logger.warning("search_index_init_failed_non_fatal")

    logger.info("app_started", app_name=settings.app_name)

    yield

    # Shutdown
    await redis_client.aclose()
    await engine.dispose()
    logger.info("app_stopped")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Policy Chatbot API",
        description="Corporate Policy Assistant Chatbot — RAG-powered policy Q&A",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Register routers
    from app.api.admin import router as admin_router
    from app.api.chat import router as chat_router
    from app.api.health import router as health_router

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(admin_router)

    _configure_cors(app)

    return app


def _configure_cors(app: FastAPI) -> None:
    """Add CORS middleware with explicit origins — never use wildcard."""
    settings = app.state.settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


# ASGI entry point for uvicorn: `uvicorn app.main:app`
app = create_app()
