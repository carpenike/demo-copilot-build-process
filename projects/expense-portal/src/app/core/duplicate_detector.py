"""Duplicate submission detection (FR-007)."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import ExpenseReport, LineItem


@dataclass
class DuplicateWarning:
    line_item_id: str
    message: str
    matching_report_number: str


async def check_duplicates(
    db: AsyncSession,
    submitter_id: uuid.UUID,
    line_items: list[LineItem],
    current_report_id: uuid.UUID,
) -> list[DuplicateWarning]:
    """Detect duplicate submissions: same employee, date, amount, vendor (FR-007).

    Only checks against previously submitted reports (not drafts).
    """
    warnings: list[DuplicateWarning] = []

    for item in line_items:
        result = await db.execute(
            select(LineItem, ExpenseReport.report_number)
            .join(ExpenseReport, LineItem.report_id == ExpenseReport.id)
            .where(
                and_(
                    ExpenseReport.submitter_id == submitter_id,
                    ExpenseReport.id != current_report_id,
                    ExpenseReport.is_deleted.is_(False),
                    ExpenseReport.status.notin_(["draft", "cancelled"]),
                    LineItem.expense_date == item.expense_date,
                    LineItem.amount == item.amount,
                    LineItem.vendor_name == item.vendor_name,
                )
            )
            .limit(1)
        )
        match = result.first()
        if match:
            warnings.append(DuplicateWarning(
                line_item_id=str(item.id),
                message=(
                    f"Possible duplicate: ${item.amount} at {item.vendor_name} "
                    f"on {item.expense_date} matches report {match.report_number}"
                ),
                matching_report_number=match.report_number,
            ))

    return warnings
