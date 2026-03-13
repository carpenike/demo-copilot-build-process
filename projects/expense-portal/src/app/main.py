"""FastAPI application factory — entry point for the Expense Portal."""

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.sessions import SessionMiddleware

from app.api.admin import router as admin_router
from app.api.approvals import router as approvals_router
from app.api.auth import router as auth_router
from app.api.expenses import router as expenses_router
from app.api.health import router as health_router
from app.api.receipts import router as receipts_router
from app.api.reports import router as reports_router
from app.config import get_settings

settings = get_settings()

# Configure structured logging (NFR-016)
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
    app = FastAPI(
        title="Expense Management Portal",
        description="Employee Expense Management Portal — Acme Corporation",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Session middleware for server-side sessions (ADR-0006)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        max_age=settings.session_max_age_seconds,
        https_only=not settings.debug,
        same_site="lax",
    )

    # Prometheus metrics instrumentation (NFR-017)
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/health", "/ready", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    # Register routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(expenses_router)
    app.include_router(receipts_router)
    app.include_router(approvals_router)
    app.include_router(reports_router)
    app.include_router(admin_router)

    return app


app = create_app()
