"""Health and readiness endpoints — no auth required."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from app.models.schemas import HealthResponse, ReadyChecks, ReadyResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> dict[str, str]:
    """Liveness probe — confirms the process is running."""
    return {"status": "healthy"}


@router.get("/ready", response_model=ReadyResponse)
async def ready(request: Request) -> Any:
    """Readiness probe — confirms all dependencies are reachable."""
    checks: dict[str, str] = {}
    all_ok = True

    # Database
    try:
        db_factory = request.app.state.db_session_factory
        async with db_factory() as session:
            await session.execute(  # type: ignore[union-attr]
                __import__("sqlalchemy").text("SELECT 1")
            )
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        all_ok = False

    # Redis
    try:
        redis_ok = await request.app.state.redis_service.check_health()
        checks["redis"] = "ok" if redis_ok else "error"
        if not redis_ok:
            all_ok = False
    except Exception:
        checks["redis"] = "error"
        all_ok = False

    # Search
    try:
        search_ok = await request.app.state.search_service.check_health()
        checks["search"] = "ok" if search_ok else "error"
        if not search_ok:
            all_ok = False
    except Exception:
        checks["search"] = "error"
        all_ok = False

    # OpenAI
    try:
        oai_ok = await request.app.state.openai_service.check_health()
        checks["openai"] = "ok" if oai_ok else "error"
        if not oai_ok:
            all_ok = False
    except Exception:
        checks["openai"] = "error"
        all_ok = False

    status_code = 200 if all_ok else 503
    body = ReadyResponse(
        status="ready" if all_ok else "not_ready",
        checks=ReadyChecks(**checks),
    )
    from fastapi.responses import JSONResponse

    return JSONResponse(content=body.model_dump(), status_code=status_code)
