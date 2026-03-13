"""Approval workflow endpoints (FR-008–FR-012)."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_client_ip, get_current_user, require_role
from app.core.approval_workflow import approve_report, reject_report, request_info
from app.models.approval import ActionToken
from app.models.database import get_db
from app.models.employee import Employee
from app.models.expense import ExpenseReport, LineItem
from app.models.schemas import (
    ApprovalResponse,
    ApproveRequest,
    EmployeeBrief,
    PendingApprovalListOut,
    PendingApprovalOut,
    RejectRequest,
    RequestInfoRequest,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/approvals", tags=["approvals"])


async def _get_pending_report(
    db: AsyncSession,
    report_id: uuid.UUID,
    current_user: Employee,
) -> ExpenseReport:
    """Load a report and verify the user is the designated approver."""
    result = await db.execute(
        select(ExpenseReport)
        .options(
            selectinload(ExpenseReport.line_items),
            selectinload(ExpenseReport.submitter),
        )
        .where(
            ExpenseReport.id == report_id,
            ExpenseReport.is_deleted.is_(False),
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # For manager approval — must be current_approver
    # For finance review — must be a finance reviewer
    is_approver = report.current_approver_id == current_user.id
    is_finance = (
        report.status == "finance_review" and current_user.is_finance_reviewer
    )
    if not (is_approver or is_finance):
        raise HTTPException(status_code=403, detail="You are not the designated approver")

    return report


@router.get("/pending", response_model=PendingApprovalListOut)
async def list_pending_approvals(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(require_role("manager", "finance_reviewer"))],
    cursor: str | None = None,
    limit: int = Query(default=20, le=100),
) -> PendingApprovalListOut:
    """List expense reports pending the current user's approval."""
    query = (
        select(ExpenseReport)
        .options(selectinload(ExpenseReport.submitter).selectinload(Employee.cost_center))
        .where(ExpenseReport.is_deleted.is_(False))
    )

    if current_user.is_finance_reviewer:
        # Finance reviewers see reports in finance_review status
        query = query.where(
            (ExpenseReport.current_approver_id == current_user.id)
            | (ExpenseReport.status == "finance_review")
        )
    else:
        query = query.where(ExpenseReport.current_approver_id == current_user.id)

    query = query.where(
        ExpenseReport.status.in_(["submitted", "finance_review"])
    ).order_by(ExpenseReport.submitted_at.asc()).limit(limit + 1)

    result = await db.execute(query)
    reports = list(result.scalars().all())

    next_cursor = None
    if len(reports) > limit:
        reports = reports[:limit]
        next_cursor = str(reports[-1].id)

    data = []
    for r in reports:
        cc_name = None
        if r.submitter and r.submitter.cost_center:
            cc_name = r.submitter.cost_center.name
        data.append(PendingApprovalOut(
            report_id=r.id,
            title=r.title,
            submitter=EmployeeBrief(
                id=r.submitter.id,
                full_name=r.submitter.full_name,
                cost_center=cc_name,
            ) if r.submitter else EmployeeBrief(id=r.submitter_id, full_name="Unknown"),
            total_amount=r.total_amount,
            line_item_count=r.line_item_count,
            submitted_at=r.submitted_at or r.created_at,
            pending_since=r.submitted_at or r.created_at,
            approval_type="finance" if r.status == "finance_review" else "manager",
        ))

    return PendingApprovalListOut(data=data, next_cursor=next_cursor, total=len(data))


@router.post("/{report_id}/approve", response_model=ApprovalResponse)
async def approve(
    report_id: uuid.UUID,
    body: ApproveRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(require_role("manager", "finance_reviewer"))],
) -> ApprovalResponse:
    """Approve an expense report."""
    report = await _get_pending_report(db, report_id, current_user)
    ip = get_client_ip(request)
    new_status, next_step = await approve_report(db, report, current_user.id, ip, body.comment)

    # Queue notifications
    from app.tasks.notification_tasks import send_approval_notification

    send_approval_notification.delay(str(report.id), new_status)

    # If fully approved, queue SAP integration
    if new_status == "approved":
        from app.tasks.integration_tasks import process_payment

        process_payment.delay(str(report.id))

    return ApprovalResponse(
        report_id=report.id,
        new_status=new_status,
        next_step=next_step,
        approved_at=report.approved_at,
    )


@router.post("/{report_id}/reject", response_model=ApprovalResponse)
async def reject(
    report_id: uuid.UUID,
    body: RejectRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(require_role("manager", "finance_reviewer"))],
) -> ApprovalResponse:
    """Reject an expense report."""
    report = await _get_pending_report(db, report_id, current_user)
    ip = get_client_ip(request)
    await reject_report(db, report, current_user.id, ip, body.reason)

    from app.tasks.notification_tasks import send_rejection_notification

    send_rejection_notification.delay(str(report.id), body.reason)

    return ApprovalResponse(
        report_id=report.id,
        new_status="rejected",
        rejected_at=report.rejected_at,
    )


@router.post("/{report_id}/request-info", response_model=ApprovalResponse)
async def request_more_info(
    report_id: uuid.UUID,
    body: RequestInfoRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(require_role("manager", "finance_reviewer"))],
) -> ApprovalResponse:
    """Request more information from the submitter."""
    report = await _get_pending_report(db, report_id, current_user)
    ip = get_client_ip(request)
    await request_info(db, report, current_user.id, ip, body.question)

    from app.tasks.notification_tasks import send_info_request_notification

    send_info_request_notification.delay(str(report.id), body.question)

    return ApprovalResponse(
        report_id=report.id,
        new_status="information_requested",
        requested_at=datetime.now(timezone.utc),
    )


@router.get("/actions/{token}")
async def handle_email_action(
    token: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> ApprovalResponse:
    """Execute an approval action via email link (single-use, time-bounded)."""
    result = await db.execute(
        select(ActionToken).where(ActionToken.token == token)
    )
    action_token = result.scalar_one_or_none()
    if not action_token:
        raise HTTPException(status_code=404, detail="Token not found")
    if action_token.is_used:
        raise HTTPException(status_code=400, detail="Token has already been used")
    if action_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token has expired")
    if action_token.approver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Token does not belong to you")

    # Mark token as used
    action_token.is_used = True
    action_token.used_at = datetime.now(timezone.utc)

    report = await _get_pending_report(db, action_token.report_id, current_user)
    ip = get_client_ip(request)

    if action_token.intended_action == "approve":
        new_status, next_step = await approve_report(db, report, current_user.id, ip)
        return ApprovalResponse(report_id=report.id, new_status=new_status, next_step=next_step, approved_at=report.approved_at)
    elif action_token.intended_action == "reject":
        await reject_report(db, report, current_user.id, ip, "Rejected via email action")
        return ApprovalResponse(report_id=report.id, new_status="rejected", rejected_at=report.rejected_at)
    else:
        raise HTTPException(status_code=400, detail="Unknown action")
