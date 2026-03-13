"""Dashboard and reporting endpoints (FR-019–FR-021)."""

import csv
import io
import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_role
from app.models.database import get_db
from app.models.employee import CostCenter, Employee
from app.models.expense import ExpenseReport, LineItem
from app.models.policy import ExpenseCategory
from app.models.schemas import (
    CategoryBreakdown,
    CostCenterBreakdown,
    EmployeeBrief,
    EmployeeSpendOut,
    FinanceReportOut,
    FinanceSummary,
    ManagerReportOut,
    StatusBreakdown,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/reports", tags=["reports"])


@router.get("/finance", response_model=FinanceReportOut)
async def finance_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(require_role("finance_reviewer"))],
    period: str = Query(description="monthly, quarterly, or yearly"),
    date_from: date | None = None,
    date_to: date | None = None,
    cost_center_id: uuid.UUID | None = None,
    category: str | None = None,
    status: str | None = None,
    format: str = "json",
) -> FinanceReportOut | StreamingResponse:  # type: ignore[return]
    """Finance reporting dashboard data."""
    base_filter = [
        ExpenseReport.is_deleted.is_(False),
        ExpenseReport.status.notin_(["draft", "cancelled"]),
    ]
    if date_from:
        base_filter.append(ExpenseReport.end_date >= date_from)
    if date_to:
        base_filter.append(ExpenseReport.start_date <= date_to)
    if status:
        base_filter.append(ExpenseReport.status == status)

    # Summary
    summary_query = select(
        func.coalesce(func.sum(ExpenseReport.total_amount), 0),
        func.count(ExpenseReport.id),
    ).where(*base_filter)
    summary_result = await db.execute(summary_query)
    total_amount, report_count = summary_result.one()
    avg = total_amount / report_count if report_count > 0 else Decimal("0")

    # By cost center
    cc_query = (
        select(
            CostCenter.name,
            func.coalesce(func.sum(ExpenseReport.total_amount), 0),
            func.count(ExpenseReport.id),
        )
        .join(Employee, ExpenseReport.submitter_id == Employee.id)
        .join(CostCenter, Employee.cost_center_id == CostCenter.id)
        .where(*base_filter)
        .group_by(CostCenter.name)
        .order_by(func.sum(ExpenseReport.total_amount).desc())
    )
    if cost_center_id:
        cc_query = cc_query.where(CostCenter.id == cost_center_id)
    cc_result = await db.execute(cc_query)
    by_cost_center = [
        CostCenterBreakdown(cost_center=row[0], total=row[1], count=row[2])
        for row in cc_result.all()
    ]

    # By category
    cat_query = (
        select(
            ExpenseCategory.name,
            func.coalesce(func.sum(LineItem.amount), 0),
            func.count(LineItem.id),
        )
        .join(ExpenseReport, LineItem.report_id == ExpenseReport.id)
        .join(ExpenseCategory, LineItem.category_id == ExpenseCategory.id)
        .where(*base_filter)
        .group_by(ExpenseCategory.name)
        .order_by(func.sum(LineItem.amount).desc())
    )
    cat_result = await db.execute(cat_query)
    by_category = [
        CategoryBreakdown(category=row[0], total=row[1], count=row[2])
        for row in cat_result.all()
    ]

    # By status
    status_query = (
        select(
            ExpenseReport.status,
            func.coalesce(func.sum(ExpenseReport.total_amount), 0),
            func.count(ExpenseReport.id),
        )
        .where(*base_filter)
        .group_by(ExpenseReport.status)
    )
    status_result = await db.execute(status_query)
    by_status = [
        StatusBreakdown(status=row[0], total=row[1], count=row[2])
        for row in status_result.all()
    ]

    report_data = FinanceReportOut(
        summary=FinanceSummary(
            total_amount=total_amount,
            report_count=report_count,
            average_amount=avg,
            period=period,
        ),
        by_cost_center=by_cost_center,
        by_category=by_category,
        by_status=by_status,
    )

    if format == "csv":
        return _finance_report_to_csv(report_data)

    return report_data


def _finance_report_to_csv(data: FinanceReportOut) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Section", "Name", "Total", "Count"])
    for cc in data.by_cost_center:
        writer.writerow(["Cost Center", cc.cost_center, str(cc.total), cc.count])
    for cat in data.by_category:
        writer.writerow(["Category", cat.category, str(cat.total), cat.count])
    for st in data.by_status:
        writer.writerow(["Status", st.status, str(st.total), st.count])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=finance_report.csv"},
    )


@router.get("/manager", response_model=ManagerReportOut)
async def manager_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(require_role("manager"))],
    period: str | None = None,
    format: str = "json",
) -> ManagerReportOut | StreamingResponse:  # type: ignore[return]
    """Manager team spend vs. budget dashboard."""
    if not current_user.cost_center:
        raise HTTPException(status_code=400, detail="No cost center assigned")

    direct_report_ids = [dr.id for dr in current_user.direct_reports]
    if not direct_report_ids:
        return ManagerReportOut(
            cost_center=current_user.cost_center.name,
            budget=current_user.cost_center.budget_amount,
            period=period or current_user.cost_center.budget_period,
            total_submitted=Decimal("0"),
            total_approved=Decimal("0"),
            remaining_budget=current_user.cost_center.budget_amount,
            by_employee=[],
        )

    # Aggregate by employee
    by_employee = []
    total_submitted = Decimal("0")
    total_approved = Decimal("0")

    for dr_id in direct_report_ids:
        dr_result = await db.execute(select(Employee).where(Employee.id == dr_id))
        dr = dr_result.scalar_one_or_none()
        if not dr:
            continue

        submitted_q = select(func.coalesce(func.sum(ExpenseReport.total_amount), 0)).where(
            ExpenseReport.submitter_id == dr_id,
            ExpenseReport.is_deleted.is_(False),
            ExpenseReport.status.notin_(["draft", "cancelled"]),
        )
        approved_q = select(func.coalesce(func.sum(ExpenseReport.total_amount), 0)).where(
            ExpenseReport.submitter_id == dr_id,
            ExpenseReport.is_deleted.is_(False),
            ExpenseReport.status.in_(["approved", "payment_processing", "paid"]),
        )
        pending_q = select(func.coalesce(func.sum(ExpenseReport.total_amount), 0)).where(
            ExpenseReport.submitter_id == dr_id,
            ExpenseReport.is_deleted.is_(False),
            ExpenseReport.status.in_(["submitted", "manager_approved", "finance_review", "information_requested"]),
        )

        sub_amt = (await db.execute(submitted_q)).scalar() or Decimal("0")
        app_amt = (await db.execute(approved_q)).scalar() or Decimal("0")
        pen_amt = (await db.execute(pending_q)).scalar() or Decimal("0")

        total_submitted += sub_amt
        total_approved += app_amt

        by_employee.append(EmployeeSpendOut(
            employee=EmployeeBrief(id=dr.id, full_name=dr.full_name),
            submitted=sub_amt,
            approved=app_amt,
            pending=pen_amt,
        ))

    budget = current_user.cost_center.budget_amount
    result = ManagerReportOut(
        cost_center=current_user.cost_center.name,
        budget=budget,
        period=period or current_user.cost_center.budget_period,
        total_submitted=total_submitted,
        total_approved=total_approved,
        remaining_budget=budget - total_approved,
        by_employee=by_employee,
    )

    if format == "csv":
        return _manager_report_to_csv(result)

    return result


def _manager_report_to_csv(data: ManagerReportOut) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Employee", "Submitted", "Approved", "Pending"])
    for emp in data.by_employee:
        writer.writerow([emp.employee.name, str(emp.submitted), str(emp.approved), str(emp.pending)])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=manager_report.csv"},
    )
