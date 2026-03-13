"""OIDC authentication routes — Microsoft Entra ID (ADR-0006)."""

import secrets

import httpx
import structlog
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import async_session_factory
from app.models.employee import Employee

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/auth", tags=["auth"])

settings = get_settings()
oauth = OAuth()
oauth.register(
    name="entra",
    client_id=settings.entra_client_id,
    client_secret=settings.entra_client_secret,
    server_metadata_url=settings.entra_openid_config_url,
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    """Initiate OIDC login — redirect to Microsoft Entra ID."""
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    redirect_uri = f"{settings.base_url}/v1/auth/callback"
    return await oauth.entra.authorize_redirect(request, redirect_uri, state=state)  # type: ignore[union-attr]


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    """OIDC callback — exchange authorization code for tokens, create session."""
    try:
        token = await oauth.entra.authorize_access_token(request)  # type: ignore[union-attr]
    except Exception:
        logger.exception("oidc_callback_failed")
        raise HTTPException(status_code=401, detail="Authentication failed")

    userinfo = token.get("userinfo", {})
    entra_oid = userinfo.get("oid") or userinfo.get("sub")
    if not entra_oid:
        raise HTTPException(status_code=401, detail="No user identifier in token")

    async with async_session_factory() as db:
        result = await db.execute(
            select(Employee).where(Employee.entra_oid == entra_oid, Employee.is_active.is_(True))
        )
        employee = result.scalar_one_or_none()

    if not employee:
        logger.warning("oidc_user_not_found", entra_oid=entra_oid)
        raise HTTPException(
            status_code=403,
            detail="Your account is not provisioned. Contact your administrator.",
        )

    request.session["user_id"] = str(employee.id)
    request.session["user_name"] = employee.full_name
    request.session["user_role"] = employee.role
    logger.info("user_authenticated", user_id=str(employee.id), name=employee.full_name)
    return RedirectResponse(url="/", status_code=302)


@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Destroy session and redirect to Entra ID logout."""
    request.session.clear()
    entra_logout_url = (
        f"{settings.entra_authority}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={settings.base_url}/login"
    )
    return RedirectResponse(url=entra_logout_url, status_code=302)
