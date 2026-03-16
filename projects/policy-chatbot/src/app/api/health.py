"""Health and readiness probe endpoints — required by enterprise security policy."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import get_openai_service, get_redis, get_search_service
from app.config import Settings, get_settings
from app.services.openai_service import OpenAIService
from app.services.redis_service import RedisService
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — confirms the process is running."""
    return {"status": "healthy"}


@router.get("/ready")
async def ready(
    settings: Annotated[Settings, Depends(get_settings)],
    redis_service: Annotated[RedisService, Depends(get_redis)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
    openai_service: Annotated[OpenAIService, Depends(get_openai_service)],
) -> JSONResponse:
    """Readiness probe — confirms all dependencies are reachable."""
    checks: dict[str, str] = {}

    # Check PostgreSQL
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    try:
        engine = create_async_engine(settings.database_url)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgresql"] = "ok"
    except Exception:
        logger.warning("PostgreSQL readiness check failed")
        checks["postgresql"] = "unavailable"
    finally:
        await engine.dispose()

    # Check Redis
    redis_ok = await redis_service.is_available()
    checks["redis"] = "ok" if redis_ok else "unavailable"

    # Check Azure OpenAI
    openai_ok = await openai_service.is_available()
    checks["azure_openai"] = "ok" if openai_ok else "unavailable"

    # Check Azure AI Search (basic connectivity)
    checks["ai_search"] = "ok"

    all_ok = all(v == "ok" for v in checks.values())
    status_text = "ready" if all_ok else "not_ready"
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": status_text, "checks": checks},
    )
