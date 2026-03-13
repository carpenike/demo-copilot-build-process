"""FastAPI dependencies — auth middleware, DB session, current user injection."""

import uuid
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.database import get_db
from app.models.employee import Employee

logger = structlog.get_logger()


async def get_session_user_id(request: Request) -> uuid.UUID:
    """Extract the authenticated employee ID from the server-side session."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        return uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session")


async def get_current_user(
    user_id: Annotated[uuid.UUID, Depends(get_session_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Employee:
    """Load the current authenticated employee with manager and direct reports."""
    result = await db.execute(
        select(Employee)
        .options(
            selectinload(Employee.cost_center),
            selectinload(Employee.direct_reports),
        )
        .where(Employee.id == user_id, Employee.is_active.is_(True))
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=401, detail="User account not found or deactivated")
    return employee


def require_role(*roles: str):
    """Dependency factory: require the current user to have one of the specified roles."""

    async def _check(current_user: Annotated[Employee, Depends(get_current_user)]) -> Employee:
        has_role = False
        for role in roles:
            if role == "manager" and current_user.is_manager:
                has_role = True
            elif role == "finance_reviewer" and current_user.is_finance_reviewer:
                has_role = True
            elif role == "finance_admin" and current_user.is_finance_admin:
                has_role = True
            elif role == "employee":
                has_role = True
        if not has_role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return _check


def get_client_ip(request: Request) -> str:
    """Extract client IP for audit logging, respecting X-Forwarded-For from API gateway."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
