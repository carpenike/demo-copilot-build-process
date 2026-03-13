"""Policy engine — validates line items against configured rules (FR-005, FR-013–FR-015)."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import LineItem, PolicyViolation
from app.models.policy import ExpenseCategory, PerDiemRate


@dataclass
class Violation:
    line_item_id: str
    rule: str
    message: str
    is_blocking: bool


async def validate_line_items(
    db: AsyncSession,
    line_items: list[LineItem],
) -> list[Violation]:
    """Run all policy checks against a list of line items. Returns violations found."""
    violations: list[Violation] = []

    for item in line_items:
        category = await _get_category(db, item.category_id)
        if not category:
            continue

        violations.extend(await _check_reimbursable(item, category))
        violations.extend(await _check_daily_limit(item, category))
        violations.extend(await _check_per_diem(db, item, category))

    return violations


async def persist_violations(
    db: AsyncSession,
    line_items: list[LineItem],
    violations: list[Violation],
) -> None:
    """Clear old violations and save new ones for these line items."""
    item_ids = [item.id for item in line_items]
    for item_id in item_ids:
        existing = await db.execute(
            select(PolicyViolation).where(PolicyViolation.line_item_id == item_id)
        )
        for row in existing.scalars():
            await db.delete(row)

    for v in violations:
        db.add(PolicyViolation(
            line_item_id=v.line_item_id,
            rule=v.rule,
            message=v.message,
            is_blocking=v.is_blocking,
        ))


async def _get_category(db: AsyncSession, category_id) -> ExpenseCategory | None:  # type: ignore[no-untyped-def]
    result = await db.execute(select(ExpenseCategory).where(ExpenseCategory.id == category_id))
    return result.scalar_one_or_none()


async def _check_reimbursable(item: LineItem, category: ExpenseCategory) -> list[Violation]:
    """FR-015: block non-reimbursable categories."""
    if not category.is_reimbursable:
        return [Violation(
            line_item_id=str(item.id),
            rule="non_reimbursable",
            message=f"Category '{category.name}' is not reimbursable",
            is_blocking=True,
        )]
    return []


async def _check_daily_limit(item: LineItem, category: ExpenseCategory) -> list[Violation]:
    """FR-013: check per-category daily limits."""
    if category.daily_limit is None:
        return []
    if item.amount > category.daily_limit:
        return [Violation(
            line_item_id=str(item.id),
            rule="daily_limit_exceeded",
            message=(
                f"{category.name} amount ${item.amount} exceeds "
                f"daily limit of ${category.daily_limit}"
            ),
            is_blocking=True,
        )]
    return []


async def _check_per_diem(
    db: AsyncSession,
    item: LineItem,
    category: ExpenseCategory,
) -> list[Violation]:
    """FR-014: flag amounts exceeding per diem rate for destination."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PerDiemRate).where(
            PerDiemRate.category_id == category.id,
            PerDiemRate.effective_from <= now,
            (PerDiemRate.effective_to.is_(None)) | (PerDiemRate.effective_to >= now),
        )
    )
    rates = result.scalars().all()
    if not rates:
        return []

    # Use the highest applicable rate as the threshold
    max_rate = max(r.rate for r in rates)
    if item.amount > max_rate:
        return [Violation(
            line_item_id=str(item.id),
            rule="per_diem_exceeded",
            message=(
                f"{category.name} amount ${item.amount} exceeds "
                f"per diem rate of ${max_rate}"
            ),
            is_blocking=False,
        )]
    return []
