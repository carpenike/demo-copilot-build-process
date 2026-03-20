"""Microsoft Entra ID JWT validation (per ADR-0012)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)
_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    """Represents the authenticated user extracted from the JWT."""

    user_id: str
    email: str
    first_name: str
    last_name: str
    roles: list[str]

    @property
    def is_admin(self) -> bool:
        return "Admin" in self.roles


async def _decode_jwt(token: str) -> dict[str, Any]:
    """Validate and decode an Entra ID JWT.

    In production this fetches JWKS from Entra ID's well-known endpoint and
    validates issuer, audience, and signature. Stubbed here for development.
    """
    # Production: use python-jose to verify RS256 signature against Entra JWKS
    # and validate iss, aud, exp, nbf claims.
    return {
        "oid": "00000000-0000-0000-0000-000000000000",
        "preferred_username": "demo.user@acme.com",
        "given_name": "Demo",
        "family_name": "User",
        "roles": ["Employee"],
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """FastAPI dependency — extracts and validates the bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    claims = await _decode_jwt(credentials.credentials)
    return CurrentUser(
        user_id=claims.get("oid", ""),
        email=claims.get("preferred_username", ""),
        first_name=claims.get("given_name", ""),
        last_name=claims.get("family_name", ""),
        roles=claims.get("roles", ["Employee"]),
    )


async def require_admin(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """FastAPI dependency — raises 403 if the user is not an admin."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user
