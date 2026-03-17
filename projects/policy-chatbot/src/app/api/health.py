"""Health and readiness endpoints.

GET /health — liveness probe (always 200 if process is running)
GET /ready  — readiness probe (checks all dependencies)
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.dependencies import DbDep, LLMDep, RedisDep, SearchDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check — indicates the process is running."""
    return {"status": "healthy"}


@router.get("/ready")
async def ready(
    db: DbDep,
    redis: RedisDep,
    search_service: SearchDep,
    llm_service: LLMDep,
    response: Response,
) -> dict[str, object]:
    """Readiness check — verifies all dependencies are reachable."""
    checks: dict[str, str] = {}

    # Database
    try:
        from sqlalchemy import text

        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    # Redis
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

    # Azure OpenAI
    openai_ok = await llm_service.check_health()
    checks["azure_openai"] = "ok" if openai_ok else "unavailable"

    # Azure AI Search
    search_ok = await search_service.check_health()
    checks["ai_search"] = "ok" if search_ok else "unavailable"

    all_ok = all(v == "ok" for v in checks.values())

    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
    }
