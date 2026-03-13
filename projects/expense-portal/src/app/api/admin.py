"""Admin panel endpoints — categories, per diem rates, thresholds (FR-024)."""

import uuid
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, require_role
from app.models.database import get_db
from app.models.employee import Employee
from app.models.policy import ApprovalThreshold, ExpenseCategory, PerDiemRate
from app.models.schemas import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    PerDiemRateOut,
    ThresholdOut,
    ThresholdUpdate,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/admin", tags=["admin"])


# --- Categories ---


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(require_role("finance_admin"))],
) -> list[CategoryOut]:
    """List all expense categories."""
    result = await db.execute(
        select(ExpenseCategory)
        .options(selectinload(ExpenseCategory.per_diem_rates))
        .where(ExpenseCategory.is_active.is_(True))
        .order_by(ExpenseCategory.name)
    )
    categories = result.scalars().all()
    return [
        CategoryOut(
            id=c.id,
            name=c.name,
            daily_limit=c.daily_limit,
            is_reimbursable=c.is_reimbursable,
            per_diem_rates=[
                PerDiemRateOut(destination=r.destination, rate=r.rate)
                for r in c.per_diem_rates
                if r.effective_to is None or r.effective_to >= datetime.now(timezone.utc)
            ],
        )
        for c in categories
    ]


@router.post("/categories", response_model=CategoryOut, status_code=201)
async def create_category(
    body: CategoryCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(require_role("finance_admin"))],
) -> CategoryOut:
    """Create a new expense category."""
    existing = await db.execute(
        select(ExpenseCategory).where(ExpenseCategory.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Category already exists")

    category = ExpenseCategory(
        name=body.name,
        daily_limit=body.daily_limit,
        is_reimbursable=body.reimbursable,
    )
    db.add(category)
    await db.flush()

    for rate in body.per_diem_rates:
        db.add(PerDiemRate(
            category_id=category.id,
            destination=rate.destination,
            rate=rate.rate,
            effective_from=datetime.now(timezone.utc),
        ))
    await db.flush()

    return CategoryOut(
        id=category.id,
        name=category.name,
        daily_limit=category.daily_limit,
        is_reimbursable=category.is_reimbursable,
        per_diem_rates=[
            PerDiemRateOut(destination=r.destination, rate=r.rate) for r in body.per_diem_rates
        ],
    )


@router.patch("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(require_role("finance_admin"))],
) -> CategoryOut:
    """Update a category's limits, reimbursable status, or per diem rates."""
    result = await db.execute(
        select(ExpenseCategory)
        .options(selectinload(ExpenseCategory.per_diem_rates))
        .where(ExpenseCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if body.name is not None:
        category.name = body.name
    if body.daily_limit is not None:
        category.daily_limit = body.daily_limit
    if body.reimbursable is not None:
        category.is_reimbursable = body.reimbursable

    if body.per_diem_rates is not None:
        # Expire old rates and create new ones
        now = datetime.now(timezone.utc)
        for old_rate in category.per_diem_rates:
            if old_rate.effective_to is None:
                old_rate.effective_to = now

        for rate in body.per_diem_rates:
            db.add(PerDiemRate(
                category_id=category.id,
                destination=rate.destination,
                rate=rate.rate,
                effective_from=now,
            ))

    await db.flush()

    # Reload
    result = await db.execute(
        select(ExpenseCategory)
        .options(selectinload(ExpenseCategory.per_diem_rates))
        .where(ExpenseCategory.id == category_id)
    )
    category = result.scalar_one()
    return CategoryOut(
        id=category.id,
        name=category.name,
        daily_limit=category.daily_limit,
        is_reimbursable=category.is_reimbursable,
        per_diem_rates=[
            PerDiemRateOut(destination=r.destination, rate=r.rate)
            for r in category.per_diem_rates
            if r.effective_to is None or r.effective_to >= datetime.now(timezone.utc)
        ],
    )


# --- Thresholds ---


@router.get("/approval-thresholds", response_model=ThresholdOut)
async def get_thresholds(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(require_role("finance_admin"))],
) -> ThresholdOut:
    """Get current approval threshold settings."""
    result = await db.execute(select(ApprovalThreshold).limit(1))
    threshold = result.scalar_one_or_none()
    if not threshold:
        return ThresholdOut(
            finance_review_threshold=500.00,
            auto_escalation_business_days=5,
            reminder_business_days=3,
        )
    return ThresholdOut(
        finance_review_threshold=threshold.finance_review_threshold,
        auto_escalation_business_days=threshold.auto_escalation_business_days,
        reminder_business_days=threshold.reminder_business_days,
    )


@router.patch("/approval-thresholds", response_model=ThresholdOut)
async def update_thresholds(
    body: ThresholdUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(require_role("finance_admin"))],
) -> ThresholdOut:
    """Update approval threshold settings."""
    result = await db.execute(select(ApprovalThreshold).limit(1))
    threshold = result.scalar_one_or_none()
    if not threshold:
        threshold = ApprovalThreshold()
        db.add(threshold)

    if body.finance_review_threshold is not None:
        threshold.finance_review_threshold = body.finance_review_threshold
    if body.auto_escalation_days is not None:
        threshold.auto_escalation_business_days = body.auto_escalation_days
    if body.reminder_days is not None:
        threshold.reminder_business_days = body.reminder_days
    threshold.updated_by = current_user.id

    await db.flush()
    return ThresholdOut(
        finance_review_threshold=threshold.finance_review_threshold,
        auto_escalation_business_days=threshold.auto_escalation_business_days,
        reminder_business_days=threshold.reminder_business_days,
    )
