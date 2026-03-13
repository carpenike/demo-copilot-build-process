"""Approval workflow — routing, state transitions, escalation (FR-008–FR-012)."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.approval import ApprovalAction
from app.models.employee import Employee
from app.models.expense import ExpenseReport
from app.models.policy import ApprovalThreshold

logger = structlog.get_logger()


async def route_for_approval(
    db: AsyncSession,
    report: ExpenseReport,
    actor_id: uuid.UUID,
    ip_address: str,
) -> Employee:
    """Route a submitted report to the submitter's manager for first-level approval (FR-008).

    Returns the assigned approver.
    """
    submitter = await _get_employee(db, report.submitter_id)
    if not submitter or not submitter.manager_id:
        raise ValueError("Submitter has no manager assigned — cannot route for approval")

    # Segregation of duties: submitter cannot approve their own report (NFR-015)
    approver = await _get_employee(db, submitter.manager_id)
    if not approver:
        raise ValueError("Manager not found in system")

    report.status = "submitted"
    report.current_approver_id = approver.id
    report.submitted_at = datetime.now(timezone.utc)

    db.add(ApprovalAction(
        report_id=report.id,
        actor_id=actor_id,
        action="submitted",
        ip_address=ip_address,
    ))

    return approver


async def approve_report(
    db: AsyncSession,
    report: ExpenseReport,
    actor_id: uuid.UUID,
    ip_address: str,
    comment: str | None = None,
) -> tuple[str, str | None]:
    """Approve a report. Returns (new_status, next_step).

    After manager approval, checks if Finance review is needed (FR-009).
    """
    threshold = await _get_threshold(db)

    if report.status == "submitted":
        # Manager approval
        new_status = "manager_approved"
        db.add(ApprovalAction(
            report_id=report.id,
            actor_id=actor_id,
            action="manager_approved",
            comment=comment,
            ip_address=ip_address,
        ))

        # Check if any line item exceeds the finance review threshold (FR-009)
        max_amount = max(
            (item.amount for item in report.line_items),
            default=Decimal("0"),
        )
        if max_amount > threshold.finance_review_threshold:
            report.status = "finance_review"
            report.current_approver_id = None  # Finance team will pick it up
            return "finance_review", "finance_review"
        else:
            report.status = "approved"
            report.current_approver_id = None
            report.approved_at = datetime.now(timezone.utc)
            return "approved", None

    elif report.status == "finance_review":
        # Finance approval
        db.add(ApprovalAction(
            report_id=report.id,
            actor_id=actor_id,
            action="finance_approved",
            comment=comment,
            ip_address=ip_address,
        ))
        report.status = "approved"
        report.current_approver_id = None
        report.approved_at = datetime.now(timezone.utc)
        return "approved", None

    else:
        raise ValueError(f"Cannot approve report in status '{report.status}'")


async def reject_report(
    db: AsyncSession,
    report: ExpenseReport,
    actor_id: uuid.UUID,
    ip_address: str,
    reason: str,
) -> None:
    """Reject a report. Employee receives notification with reason (FR-012)."""
    if report.status not in ("submitted", "finance_review"):
        raise ValueError(f"Cannot reject report in status '{report.status}'")

    db.add(ApprovalAction(
        report_id=report.id,
        actor_id=actor_id,
        action="rejected",
        comment=reason,
        ip_address=ip_address,
    ))
    report.status = "rejected"
    report.current_approver_id = None
    report.rejected_at = datetime.now(timezone.utc)


async def request_info(
    db: AsyncSession,
    report: ExpenseReport,
    actor_id: uuid.UUID,
    ip_address: str,
    question: str,
) -> None:
    """Request more information from the submitter (FR-010)."""
    if report.status not in ("submitted", "finance_review"):
        raise ValueError(f"Cannot request info on report in status '{report.status}'")

    db.add(ApprovalAction(
        report_id=report.id,
        actor_id=actor_id,
        action="information_requested",
        comment=question,
        ip_address=ip_address,
    ))
    report.status = "information_requested"
    report.current_approver_id = None


async def escalate_report(
    db: AsyncSession,
    report: ExpenseReport,
) -> Employee | None:
    """Escalate to the approver's manager if no action after deadline (FR-011).

    Returns the new approver, or None if escalation chain is exhausted.
    """
    if not report.current_approver_id:
        return None

    current_approver = await _get_employee(db, report.current_approver_id)
    if not current_approver or not current_approver.manager_id:
        logger.warning(
            "escalation_chain_exhausted",
            report_id=str(report.id),
            approver_id=str(report.current_approver_id),
        )
        return None

    new_approver = await _get_employee(db, current_approver.manager_id)
    if not new_approver:
        return None

    db.add(ApprovalAction(
        report_id=report.id,
        actor_id=current_approver.id,
        action="escalated",
        comment=f"Auto-escalated: no action within deadline",
    ))
    report.current_approver_id = new_approver.id
    logger.info(
        "report_escalated",
        report_id=str(report.id),
        from_approver=str(current_approver.id),
        to_approver=str(new_approver.id),
    )
    return new_approver


async def _get_employee(db: AsyncSession, employee_id: uuid.UUID) -> Employee | None:
    result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.direct_reports))
        .where(Employee.id == employee_id)
    )
    return result.scalar_one_or_none()


async def _get_threshold(db: AsyncSession) -> ApprovalThreshold:
    result = await db.execute(select(ApprovalThreshold).limit(1))
    threshold = result.scalar_one_or_none()
    if not threshold:
        # Return defaults if no row exists yet
        return ApprovalThreshold(
            finance_review_threshold=Decimal("500.00"),
            auto_escalation_business_days=5,
            reminder_business_days=3,
        )
    return threshold
