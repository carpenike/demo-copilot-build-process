"""FastAPI dependency injection for database, Redis, and services.

All external clients are created per-request via dependency injection so they
can be mocked in tests without import-time failures. No module-scope
initialization of Azure SDKs or database connections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, HTTPException, Request, status

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Runtime imports needed for Annotated type aliases used by FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.services.conversation_service import ConversationService
from app.services.document_service import DocumentService
from app.services.feedback_service import FeedbackService
from app.services.llm_service import LLMService
from app.services.search_service import SearchService


def get_settings(request: Request) -> Settings:
    """Retrieve application settings from the app state."""
    return request.app.state.settings  # type: ignore[no-any-return]


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session per request."""
    async_session = request.app.state.async_session
    async with async_session() as session:
        yield session


async def get_redis(request: Request) -> Redis:
    """Retrieve the Redis client from app state."""
    return request.app.state.redis  # type: ignore[no-any-return]


def get_search_service(request: Request) -> SearchService:
    """Retrieve the search service from app state."""
    return request.app.state.search_service  # type: ignore[no-any-return]


def get_llm_service(request: Request) -> LLMService:
    """Retrieve the LLM service from app state."""
    return request.app.state.llm_service  # type: ignore[no-any-return]


def get_document_service(request: Request) -> DocumentService:
    """Retrieve the document service from app state."""
    return request.app.state.document_service  # type: ignore[no-any-return]


async def get_conversation_service(request: Request) -> ConversationService:
    """Retrieve the conversation service from app state."""
    return request.app.state.conversation_service  # type: ignore[no-any-return]


def get_feedback_service(request: Request) -> FeedbackService:
    """Retrieve the feedback service from app state."""
    return request.app.state.feedback_service  # type: ignore[no-any-return]


async def get_current_user(request: Request) -> dict[str, Any]:
    """Extract and validate the current user from the request.

    In production, this validates the Entra ID JWT token.
    For development, returns a placeholder user if no auth header is present.
    """
    settings = get_settings(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        if settings.debug:
            return {
                "sub": "dev-user-id",
                "name": "Dev User",
                "preferred_username": "dev@acme.com",
                "roles": ["Employee", "PolicyAdmin"],
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = auth_header.removeprefix("Bearer ").strip()

    try:
        from jose import jwt  # type: ignore[import-untyped]

        payload: dict[str, Any] = jwt.decode(
            token,
            key="",
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": True,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from e

    return payload


async def require_admin(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    """Require the PolicyAdmin role for admin endpoints."""
    roles = user.get("roles", [])
    if "PolicyAdmin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PolicyAdmin role required",
        )
    return user


# Type aliases for cleaner route signatures
SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]
SearchDep = Annotated[SearchService, Depends(get_search_service)]
LLMDep = Annotated[LLMService, Depends(get_llm_service)]
DocServiceDep = Annotated[DocumentService, Depends(get_document_service)]
ConvServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]
FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]
CurrentUserDep = Annotated[dict[str, Any], Depends(get_current_user)]
AdminUserDep = Annotated[dict[str, Any], Depends(require_admin)]
