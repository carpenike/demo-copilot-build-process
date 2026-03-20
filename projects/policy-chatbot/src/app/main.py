"""FastAPI application factory with lifespan context manager."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise external service clients on startup, clean up on shutdown."""
    settings = Settings()

    # --- Azure Monitor (non-fatal) ---
    if settings.applicationinsights_connection_string:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(
                connection_string=settings.applicationinsights_connection_string,
            )
        except Exception:
            logger.warning("azure_monitor_init_failed_non_fatal")

    # --- Database ---
    from app.services.database import create_engine

    app.state.db_session_factory = create_engine(settings)

    # --- Redis ---
    from app.services.redis_client import RedisService

    app.state.redis_service = RedisService(settings)

    # --- Blob Storage ---
    from app.services.blob import BlobService

    app.state.blob_service = BlobService(settings)

    # --- Azure AI Search ---
    from app.services.search import SearchService

    app.state.search_service = SearchService(settings)
    await app.state.search_service.ensure_index()

    # --- Azure OpenAI ---
    from app.services.openai_client import OpenAIService

    app.state.openai_service = OpenAIService(settings)

    # --- ServiceNow ---
    from app.services.servicenow import ServiceNowClient

    app.state.servicenow_client = ServiceNowClient(settings)

    # --- Graph ---
    from app.services.graph import GraphService

    app.state.graph_service = GraphService(settings)

    logger.info("startup_complete")
    yield
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    """Build the FastAPI application — CORS uses Settings() directly."""
    settings = Settings()

    app = FastAPI(
        title="Policy Chatbot API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — explicit origins only (enterprise-standards.md: no wildcard)
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    # --- Register routers ---
    from app.api.admin import router as admin_router
    from app.api.analytics import router as analytics_router
    from app.api.chat import router as chat_router
    from app.api.feedback import router as feedback_router
    from app.api.health import router as health_router

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(feedback_router)
    app.include_router(admin_router)
    app.include_router(analytics_router)

    return app


app = create_app()
