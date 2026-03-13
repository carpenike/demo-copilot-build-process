"""Health, readiness, and metrics endpoints (NFR-017, NFR-019)."""

import structlog
from fastapi import APIRouter
from sqlalchemy import text

from app.models.database import async_session_factory
from app.models.schemas import HealthResponse, ReadyResponse

logger = structlog.get_logger()
router = APIRouter(tags=["operations"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Kubernetes liveness probe."""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    """Kubernetes readiness probe — checks database connectivity."""
    checks: dict[str, str] = {}

    try:
        async with async_session_factory() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        logger.exception("readiness_check_database_failed")

    # Redis check via Celery broker
    try:
        from app.tasks.celery_app import celery_app

        celery_app.control.ping(timeout=2.0)
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
        logger.exception("readiness_check_redis_failed")

    all_ok = all(v == "ok" for v in checks.values())
    status = "ready" if all_ok else "not_ready"

    if not all_ok:
        from fastapi.responses import JSONResponse

        return JSONResponse(  # type: ignore[return-value]
            status_code=503,
            content=ReadyResponse(status=status, checks=checks).model_dump(),
        )

    return ReadyResponse(status=status, checks=checks)
