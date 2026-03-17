"""FastAPI application factory — entry point for the Policy Chatbot."""

import logging
import os

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.config import get_settings

settings = get_settings()

# Configure Azure Monitor OpenTelemetry (ADR-0010, enterprise standards)
# Guarded: only initialize when APPLICATIONINSIGHTS_CONNECTION_STRING is set
# and we're not in debug/test mode. This avoids import failures in test environments
# where azure-monitor-opentelemetry has SDK version conflicts.
if not settings.debug and os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor()
    except ImportError:
        logging.getLogger(__name__).warning(
            "azure-monitor-opentelemetry not available — telemetry disabled"
        )

# Configure structured logging — JSON to stdout for Azure Monitor ingestion
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Corporate Policy Assistant Chatbot",
        description=(
            "Conversational AI that answers policy questions"
            " with citations and actionable checklists"
        ),
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS — explicit origin allowlist only, never wildcard (enterprise security policy)
    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH"],
            allow_headers=["Authorization", "Content-Type"],
        )

    # Register routers
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(admin_router)

    return app


app = create_app()
