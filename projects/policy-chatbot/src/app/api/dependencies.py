"""Shared FastAPI dependencies — auth, database sessions, service injection."""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings, get_settings
from app.core.rag_pipeline import RAGPipeline
from app.services.blob_service import BlobService
from app.services.graph_service import GraphService
from app.services.openai_service import OpenAIService
from app.services.redis_service import RedisService
from app.services.search_service import SearchService
from app.services.servicenow_service import ServiceNowService

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer()

# --- Singletons (created once, reused across requests) ---

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_redis_service: RedisService | None = None
_search_service: SearchService | None = None
_openai_service: OpenAIService | None = None
_blob_service: BlobService | None = None
_servicenow_service: ServiceNowService | None = None
_graph_service: GraphService | None = None
_jwks_cache: dict | None = None  # type: ignore[type-arg]


def _get_engine(settings: Settings) -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_size=20,
            max_overflow=10,
            echo=settings.debug,
        )
    return _engine


def _get_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        engine = _get_engine(settings)
        _session_factory = async_sessionmaker(
            engine,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session per request."""
    factory = _get_session_factory(settings)
    async with factory() as session:
        yield session


def get_redis(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedisService:
    """Return the singleton Redis service."""
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService(settings)
    return _redis_service


def get_search_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchService:
    """Return the singleton Azure AI Search service."""
    global _search_service
    if _search_service is None:
        _search_service = SearchService(settings)
    return _search_service


def get_openai_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> OpenAIService:
    """Return the singleton Azure OpenAI service."""
    global _openai_service
    if _openai_service is None:
        _openai_service = OpenAIService(settings)
    return _openai_service


def get_blob_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> BlobService:
    """Return the singleton Blob Storage service."""
    global _blob_service
    if _blob_service is None:
        _blob_service = BlobService(settings)
    return _blob_service


def get_servicenow_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ServiceNowService:
    """Return the singleton ServiceNow service."""
    global _servicenow_service
    if _servicenow_service is None:
        _servicenow_service = ServiceNowService(settings)
    return _servicenow_service


def get_graph_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GraphService:
    """Return the singleton Graph API service."""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService(settings)
    return _graph_service


def get_rag_pipeline(
    search_service: Annotated[SearchService, Depends(get_search_service)],
    openai_service: Annotated[OpenAIService, Depends(get_openai_service)],
    redis_service: Annotated[RedisService, Depends(get_redis)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RAGPipeline:
    """Build a RAG pipeline with injected services."""
    return RAGPipeline(
        search_service=search_service,
        openai_service=openai_service,
        redis_service=redis_service,
        top_k=settings.rag_top_k,
        confidence_threshold=settings.rag_confidence_threshold,
        max_conversation_history=settings.rag_max_conversation_history,
    )


async def _get_jwks(settings: Settings) -> dict:  # type: ignore[type-arg]
    """Fetch and cache JWKS keys from Entra ID for JWT validation."""
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            openid_config_url = (
                f"https://login.microsoftonline.com/{settings.entra_tenant_id}"
                "/v2.0/.well-known/openid-configuration"
            )
            config_resp = await client.get(openid_config_url)
            config_resp.raise_for_status()
            jwks_uri = config_resp.json()["jwks_uri"]
            jwks_resp = await client.get(jwks_uri)
            jwks_resp.raise_for_status()
            _jwks_cache = jwks_resp.json()
    return _jwks_cache


class AuthenticatedUser:
    """Represents the authenticated user extracted from a validated JWT."""

    def __init__(self, user_id: str, roles: list[str], name: str) -> None:
        self.user_id = user_id
        self.roles = roles
        self.name = name

    @property
    def is_admin(self) -> bool:
        return "Administrator" in self.roles


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    """Validate the Entra ID JWT and extract user claims (ADR-0011)."""
    token = credentials.credentials

    # Fetch JWKS keys for JWT validation
    jwks = await _get_jwks(settings)

    # Decode and validate the JWT claims
    try:
        import jose.jwt as jose_jwt  # type: ignore[import-untyped]

        claims = jose_jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.entra_client_id,
            issuer=settings.entra_issuer,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user_id = claims.get("oid", claims.get("sub", ""))
    roles = claims.get("roles", ["Employee"])
    name = claims.get("name", "")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
        )

    return AuthenticatedUser(user_id=user_id, roles=roles, name=name)


def require_admin(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """Dependency that requires the Administrator App Role (NFR-010)."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )
    return user
