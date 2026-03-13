"""Expense report and line item CRUD endpoints."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_client_ip, get_current_user, require_role
from app.core.approval_workflow import route_for_approval
from app.core.duplicate_detector import check_duplicates
from app.core.policy_engine import persist_violations, validate_line_items
from app.models.database import get_db
from app.models.employee import Employee
from app.models.expense import ExpenseReport, LineItem, PolicyViolation
from app.models.policy import ExpenseCategory
from app.models.schemas import (
    ApprovalHistoryEntry,
    EmployeeBrief,
    LineItemCreate,
    LineItemOut,
    LineItemUpdate,
    PolicyViolationOut,
    PolicyViolationsSummary,
    ReportCreate,
    ReportDetailOut,
    ReportListOut,
    ReportSummaryOut,
    ReportUpdate,
    SubmitRequest,
    SubmitResponse,
    SubmitterDetail,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/expenses", tags=["expenses"])


async def _next_report_number(db: AsyncSession) -> str:
    """Generate the next sequential report number (RPT-NNNN)."""
    result = await db.execute(
        select(func.count()).select_from(ExpenseReport)
    )
    count = result.scalar() or 0
    return f"RPT-{count + 1:04d}"


async def _get_report_or_404(
    db: AsyncSession,
    report_id: uuid.UUID,
    load_items: bool = False,
) -> ExpenseReport:
    query = select(ExpenseReport).where(
        ExpenseReport.id == report_id,
        ExpenseReport.is_deleted.is_(False),
    )
    if load_items:
        query = query.options(
            selectinload(ExpenseReport.line_items).selectinload(LineItem.category),
            selectinload(ExpenseReport.line_items).selectinload(LineItem.receipt),
            selectinload(ExpenseReport.line_items).selectinload(LineItem.policy_violations),
            selectinload(ExpenseReport.approval_actions),
            selectinload(ExpenseReport.submitter),
        )
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _check_report_owner(report: ExpenseReport, user: Employee) -> None:
    if report.submitter_id != user.id:
        raise HTTPException(status_code=403, detail="Not the owner of this report")


def _check_report_editable(report: ExpenseReport) -> None:
    if not report.is_editable:
        raise HTTPException(status_code=409, detail="Report is not editable in current status")


def _can_view_report(report: ExpenseReport, user: Employee) -> bool:
    """Check if user has permission to view this report."""
    if report.submitter_id == user.id:
        return True
    if user.is_finance_reviewer:
        return True
    # Manager can view direct reports' submissions
    direct_report_ids = {dr.id for dr in user.direct_reports}
    return report.submitter_id in direct_report_ids


def _build_line_item_out(item: LineItem) -> LineItemOut:
    receipt_url = None
    if item.receipt:
        receipt_url = f"/v1/receipts/{item.receipt.id}"
    return LineItemOut(
        id=item.id,
        expense_date=item.expense_date,
        category=item.category.name if item.category else "Unknown",
        vendor_name=item.vendor_name,
        amount=item.amount,
        currency=item.currency,
        description=item.description,
        receipt_url=receipt_url,
        policy_violations=[
            PolicyViolationOut(
                line_item_id=v.line_item_id,
                rule=v.rule,
                message=v.message,
                is_blocking=v.is_blocking,
            )
            for v in item.policy_violations
        ],
        ocr_status=item.ocr_status,
        created_at=item.created_at,
    )


# --- Report endpoints ---


@router.get("/reports", response_model=ReportListOut)
async def list_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(get_current_user)],
    cursor: str | None = None,
    limit: int = Query(default=20, le=100),
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> ReportListOut:
    """List expense reports for the current user (own reports or direct reports')."""
    query = (
        select(ExpenseReport)
        .options(selectinload(ExpenseReport.submitter).selectinload(Employee.cost_center))
        .where(ExpenseReport.is_deleted.is_(False))
    )

    # Employees see their own; managers also see direct reports'
    if current_user.is_manager or current_user.is_finance_reviewer:
        direct_report_ids = [dr.id for dr in current_user.direct_reports]
        submitter_ids = [current_user.id] + direct_report_ids
        query = query.where(ExpenseReport.submitter_id.in_(submitter_ids))
    else:
        query = query.where(ExpenseReport.submitter_id == current_user.id)

    if status:
        query = query.where(ExpenseReport.status == status)

    query = query.order_by(ExpenseReport.updated_at.desc()).limit(limit + 1)

    result = await db.execute(query)
    reports = list(result.scalars().all())

    next_cursor = None
    if len(reports) > limit:
        reports = reports[:limit]
        next_cursor = str(reports[-1].id)

    # Count total
    count_query = select(func.count()).select_from(ExpenseReport).where(
        ExpenseReport.submitter_id == current_user.id,
        ExpenseReport.is_deleted.is_(False),
    )
    total = (await db.execute(count_query)).scalar() or 0

    data = []
    for r in reports:
        submitter_brief = None
        if r.submitter:
            cc_name = r.submitter.cost_center.name if r.submitter.cost_center else None
            submitter_brief = EmployeeBrief(
                id=r.submitter.id, full_name=r.submitter.full_name, cost_center=cc_name
            )
        data.append(ReportSummaryOut(
            id=r.id,
            title=r.title,
            status=r.status,
            start_date=r.start_date,
            end_date=r.end_date,
            business_purpose=r.business_purpose,
            total_amount=r.total_amount,
            currency=r.currency,
            line_item_count=r.line_item_count,
            submitted_at=r.submitted_at,
            submitter=submitter_brief,
            created_at=r.created_at,
            updated_at=r.updated_at,
        ))

    return ReportListOut(data=data, next_cursor=next_cursor, total=total)


@router.post("/reports", response_model=ReportSummaryOut, status_code=201)
async def create_report(
    body: ReportCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> ReportSummaryOut:
    """Create a new expense report."""
    if body.end_date < body.start_date:
        raise HTTPException(status_code=400, detail="end_date must be >= start_date")

    report = ExpenseReport(
        report_number=await _next_report_number(db),
        submitter_id=current_user.id,
        title=body.title,
        start_date=body.start_date,
        end_date=body.end_date,
        business_purpose=body.business_purpose,
        status="draft",
        currency="USD",
    )
    db.add(report)
    await db.flush()

    return ReportSummaryOut(
        id=report.id,
        title=report.title,
        status=report.status,
        start_date=report.start_date,
        end_date=report.end_date,
        business_purpose=report.business_purpose,
        total_amount=report.total_amount,
        currency=report.currency,
        line_item_count=0,
        submitted_at=None,
        submitter=None,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.get("/reports/{report_id}", response_model=ReportDetailOut)
async def get_report(
    report_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> ReportDetailOut:
    """Get full details of an expense report."""
    report = await _get_report_or_404(db, report_id, load_items=True)
    if not _can_view_report(report, current_user):
        raise HTTPException(status_code=403, detail="You do not have permission to view this report")

    submitter_detail = None
    if report.submitter:
        submitter_detail = SubmitterDetail(
            id=report.submitter.id,
            full_name=report.submitter.full_name,
            cost_center=report.submitter.cost_center.name if report.submitter.cost_center else None,
            cost_center_id=report.submitter.cost_center_id,
        )

    items_out = [_build_line_item_out(item) for item in report.line_items]

    history = [
        ApprovalHistoryEntry(
            action=a.action,
            actor=a.actor.full_name if a.actor else "System",
            created_at=a.created_at,
            comment=a.comment,
        )
        for a in report.approval_actions
    ]

    blocking = sum(
        1 for item in report.line_items for v in item.policy_violations if v.is_blocking
    )
    warnings = sum(
        1 for item in report.line_items for v in item.policy_violations if not v.is_blocking
    )

    return ReportDetailOut(
        id=report.id,
        title=report.title,
        status=report.status,
        start_date=report.start_date,
        end_date=report.end_date,
        business_purpose=report.business_purpose,
        total_amount=report.total_amount,
        currency=report.currency,
        submitter=submitter_detail,
        line_items=items_out,
        approval_history=history,
        policy_violations_summary=PolicyViolationsSummary(blocking=blocking, warnings=warnings),
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.patch("/reports/{report_id}", response_model=ReportDetailOut)
async def update_report(
    report_id: uuid.UUID,
    body: ReportUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> ReportDetailOut:
    """Update an expense report (draft or rejected only)."""
    report = await _get_report_or_404(db, report_id, load_items=True)
    _check_report_owner(report, current_user)
    _check_report_editable(report)

    if body.title is not None:
        report.title = body.title
    if body.start_date is not None:
        report.start_date = body.start_date
    if body.end_date is not None:
        report.end_date = body.end_date
    if body.business_purpose is not None:
        report.business_purpose = body.business_purpose

    if report.end_date < report.start_date:
        raise HTTPException(status_code=400, detail="end_date must be >= start_date")

    await db.flush()
    return await get_report(report_id, db, current_user)


@router.post("/reports/{report_id}/submit", response_model=SubmitResponse)
async def submit_report(
    report_id: uuid.UUID,
    body: SubmitRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> SubmitResponse:
    """Submit a report for approval. Validates policy and checks duplicates."""
    report = await _get_report_or_404(db, report_id, load_items=True)
    _check_report_owner(report, current_user)
    _check_report_editable(report)

    if not report.line_items:
        raise HTTPException(status_code=400, detail="Report has no line items")

    # Policy validation (FR-005)
    violations = await validate_line_items(db, report.line_items)
    await persist_violations(db, report.line_items, violations)

    blocking_violations = [v for v in violations if v.is_blocking]
    if blocking_violations:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "https://expenses.acme.com/errors/policy-violation",
                "title": "Policy Violations",
                "status": 422,
                "detail": f"{len(blocking_violations)} policy violation(s) must be resolved.",
                "violations": [
                    {
                        "line_item_id": v.line_item_id,
                        "rule": v.rule,
                        "message": v.message,
                        "blocking": v.is_blocking,
                    }
                    for v in violations
                ],
            },
        )

    # Duplicate detection (FR-007)
    duplicates = await check_duplicates(db, current_user.id, report.line_items, report.id)
    if duplicates and not body.acknowledge_warnings:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "https://expenses.acme.com/errors/policy-violation",
                "title": "Duplicate Warnings",
                "status": 422,
                "detail": f"{len(duplicates)} possible duplicate(s) detected.",
                "violations": [
                    {
                        "line_item_id": d.line_item_id,
                        "rule": "duplicate_detected",
                        "message": d.message,
                        "blocking": False,
                    }
                    for d in duplicates
                ],
            },
        )

    # Recalculate total
    report.total_amount = sum(item.amount for item in report.line_items)

    # Route for approval (FR-008)
    ip = get_client_ip(request)
    approver = await route_for_approval(db, report, current_user.id, ip)

    # Queue notification
    from app.tasks.notification_tasks import send_submission_notification

    send_submission_notification.delay(str(report.id), str(approver.id))

    await db.flush()

    return SubmitResponse(
        id=report.id,
        status=report.status,
        submitted_at=report.submitted_at,  # type: ignore[arg-type]
        routed_to=EmployeeBrief(
            id=approver.id,
            full_name=approver.full_name,
            cost_center=approver.cost_center.name if approver.cost_center else None,
        ),
    )


# --- Line Item endpoints ---


@router.post("/reports/{report_id}/line-items", response_model=LineItemOut, status_code=201)
async def add_line_item(
    report_id: uuid.UUID,
    body: LineItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> LineItemOut:
    """Add a line item to an expense report."""
    report = await _get_report_or_404(db, report_id, load_items=True)
    _check_report_owner(report, current_user)
    _check_report_editable(report)

    # Validate category exists
    cat_result = await db.execute(
        select(ExpenseCategory).where(
            ExpenseCategory.name == body.category,
            ExpenseCategory.is_active.is_(True),
        )
    )
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=400, detail=f"Invalid category: {body.category}")

    next_order = len(report.line_items)
    item = LineItem(
        report_id=report.id,
        expense_date=body.date,
        category_id=category.id,
        vendor_name=body.vendor_name,
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        sort_order=next_order,
    )
    db.add(item)
    await db.flush()

    # Reload with relationships
    result = await db.execute(
        select(LineItem)
        .options(
            selectinload(LineItem.category),
            selectinload(LineItem.receipt),
            selectinload(LineItem.policy_violations),
        )
        .where(LineItem.id == item.id)
    )
    item = result.scalar_one()
    return _build_line_item_out(item)


@router.patch("/reports/{report_id}/line-items/{item_id}", response_model=LineItemOut)
async def update_line_item(
    report_id: uuid.UUID,
    item_id: uuid.UUID,
    body: LineItemUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> LineItemOut:
    """Update a line item."""
    report = await _get_report_or_404(db, report_id)
    _check_report_owner(report, current_user)
    _check_report_editable(report)

    result = await db.execute(
        select(LineItem)
        .options(
            selectinload(LineItem.category),
            selectinload(LineItem.receipt),
            selectinload(LineItem.policy_violations),
        )
        .where(LineItem.id == item_id, LineItem.report_id == report_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")

    if body.date is not None:
        item.expense_date = body.date
    if body.vendor_name is not None:
        item.vendor_name = body.vendor_name
    if body.amount is not None:
        item.amount = body.amount
    if body.currency is not None:
        item.currency = body.currency
    if body.description is not None:
        item.description = body.description
    if body.category is not None:
        cat_result = await db.execute(
            select(ExpenseCategory).where(
                ExpenseCategory.name == body.category,
                ExpenseCategory.is_active.is_(True),
            )
        )
        category = cat_result.scalar_one_or_none()
        if not category:
            raise HTTPException(status_code=400, detail=f"Invalid category: {body.category}")
        item.category_id = category.id

    await db.flush()
    return _build_line_item_out(item)


@router.delete("/reports/{report_id}/line-items/{item_id}", status_code=204)
async def delete_line_item(
    report_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> None:
    """Remove a line item from a report."""
    report = await _get_report_or_404(db, report_id)
    _check_report_owner(report, current_user)
    _check_report_editable(report)

    result = await db.execute(
        select(LineItem).where(LineItem.id == item_id, LineItem.report_id == report_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")

    await db.delete(item)
