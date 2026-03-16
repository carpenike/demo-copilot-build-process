"""Notification tasks — email + in-app notifications (FR-022, FR-023)."""

import secrets
from datetime import datetime, timedelta, timezone

import structlog
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.email import send_email

logger = structlog.get_logger()
settings = get_settings()


def _get_sync_session() -> Session:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url)
    return sessionmaker(bind=engine)()


def _create_notification(
    db: Session,
    recipient_id: str,
    report_id: str,
    channel: str,
    event_type: str,
    subject: str,
    body: str,
) -> None:
    """Create a notification record in the database."""
    from app.models.notification import Notification

    notification = Notification(
        recipient_id=recipient_id,
        report_id=report_id,
        channel=channel,
        event_type=event_type,
        subject=subject,
        body=body,
        sent_at=datetime.now(timezone.utc) if channel == "email" else None,
    )
    db.add(notification)


def _create_action_token(
    db: Session,
    report_id: str,
    approver_id: str,
    action: str,
) -> str:
    """Create a single-use, time-bounded email action token (ADR-0004)."""
    from app.models.approval import ActionToken

    token = secrets.token_urlsafe(32)
    db.add(ActionToken(
        report_id=report_id,
        approver_id=approver_id,
        token=token,
        intended_action=action,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    ))
    return token


@shared_task(name="app.tasks.notification_tasks.send_submission_notification", queue="notifications")
def send_submission_notification(report_id: str, approver_id: str) -> None:
    """Notify the approver that a new expense report needs review."""
    from app.models.employee import Employee
    from app.models.expense import ExpenseReport

    db = _get_sync_session()
    try:
        report = db.execute(select(ExpenseReport).where(ExpenseReport.id == report_id)).scalar_one()
        approver = db.execute(select(Employee).where(Employee.id == approver_id)).scalar_one()
        submitter = db.execute(select(Employee).where(Employee.id == report.submitter_id)).scalar_one()

        approve_token = _create_action_token(db, report_id, approver_id, "approve")
        reject_token = _create_action_token(db, report_id, approver_id, "reject")

        subject = f"Expense Report Pending Your Approval: {report.title}"
        body = (
            f"<p>{submitter.full_name} has submitted expense report "
            f"<strong>{report.report_number}</strong> ({report.title}) "
            f"for ${report.total_amount}.</p>"
            f'<p><a href="{settings.base_url}/v1/approvals/actions/{approve_token}">Approve</a> | '
            f'<a href="{settings.base_url}/v1/approvals/actions/{reject_token}">Reject</a></p>'
        )

        send_email(approver.email, subject, body)
        _create_notification(db, approver_id, report_id, "email", "submitted", subject, body)
        _create_notification(db, str(report.submitter_id), report_id, "in_app", "submitted",
                            "Expense Report Submitted", f"Your report {report.report_number} has been submitted for approval.")
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("notification_failed", report_id=report_id, type="submission")
        raise
    finally:
        db.close()


@shared_task(name="app.tasks.notification_tasks.send_approval_notification", queue="notifications")
def send_approval_notification(report_id: str, new_status: str) -> None:
    """Notify the employee that their expense report was approved."""
    from app.models.employee import Employee
    from app.models.expense import ExpenseReport

    db = _get_sync_session()
    try:
        report = db.execute(select(ExpenseReport).where(ExpenseReport.id == report_id)).scalar_one()
        submitter = db.execute(select(Employee).where(Employee.id == report.submitter_id)).scalar_one()

        if new_status == "approved":
            subject = f"Expense Report Approved: {report.title}"
            body = f"<p>Your expense report <strong>{report.report_number}</strong> has been fully approved. Payment processing will begin shortly.</p>"
        elif new_status == "finance_review":
            subject = f"Expense Report Manager-Approved: {report.title}"
            body = f"<p>Your expense report <strong>{report.report_number}</strong> has been approved by your manager and is now pending Finance review.</p>"
        else:
            subject = f"Expense Report Update: {report.title}"
            body = f"<p>Your expense report <strong>{report.report_number}</strong> status is now: {new_status}.</p>"

        send_email(submitter.email, subject, body)
        _create_notification(db, str(report.submitter_id), report_id, "email", "approved", subject, body)
        _create_notification(db, str(report.submitter_id), report_id, "in_app", "approved", subject, body)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("notification_failed", report_id=report_id, type="approval")
        raise
    finally:
        db.close()


@shared_task(name="app.tasks.notification_tasks.send_rejection_notification", queue="notifications")
def send_rejection_notification(report_id: str, reason: str) -> None:
    """Notify the employee that their expense report was rejected (FR-012)."""
    from app.models.employee import Employee
    from app.models.expense import ExpenseReport

    db = _get_sync_session()
    try:
        report = db.execute(select(ExpenseReport).where(ExpenseReport.id == report_id)).scalar_one()
        submitter = db.execute(select(Employee).where(Employee.id == report.submitter_id)).scalar_one()

        subject = f"Expense Report Rejected: {report.title}"
        body = (
            f"<p>Your expense report <strong>{report.report_number}</strong> has been rejected.</p>"
            f"<p><strong>Reason:</strong> {reason}</p>"
            f'<p><a href="{settings.base_url}/expenses/{report_id}/edit">Edit and Resubmit</a></p>'
        )

        send_email(submitter.email, subject, body)
        _create_notification(db, str(report.submitter_id), report_id, "email", "rejected", subject, body)
        _create_notification(db, str(report.submitter_id), report_id, "in_app", "rejected", subject, body)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("notification_failed", report_id=report_id, type="rejection")
        raise
    finally:
        db.close()


@shared_task(name="app.tasks.notification_tasks.send_info_request_notification", queue="notifications")
def send_info_request_notification(report_id: str, question: str) -> None:
    """Notify the employee that more information was requested."""
    from app.models.employee import Employee
    from app.models.expense import ExpenseReport

    db = _get_sync_session()
    try:
        report = db.execute(select(ExpenseReport).where(ExpenseReport.id == report_id)).scalar_one()
        submitter = db.execute(select(Employee).where(Employee.id == report.submitter_id)).scalar_one()

        subject = f"More Information Requested: {report.title}"
        body = (
            f"<p>The reviewer has requested more information on your expense report "
            f"<strong>{report.report_number}</strong>.</p>"
            f"<p><strong>Question:</strong> {question}</p>"
            f'<p><a href="{settings.base_url}/expenses/{report_id}">View Report</a></p>'
        )

        send_email(submitter.email, subject, body)
        _create_notification(db, str(report.submitter_id), report_id, "email", "info_requested", subject, body)
        _create_notification(db, str(report.submitter_id), report_id, "in_app", "info_requested", subject, body)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("notification_failed", report_id=report_id, type="info_request")
        raise
    finally:
        db.close()
