"""Scheduled tasks — Workday sync, approval escalation, reminders (FR-011, FR-016, FR-023)."""

from datetime import datetime, timedelta, timezone

import structlog
from celery import shared_task
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


def _get_sync_session() -> Session:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url)
    return sessionmaker(bind=engine)()


@shared_task(name="app.tasks.scheduled_tasks.sync_workday", queue="scheduled")
def sync_workday() -> dict:
    """Nightly sync of employee, manager hierarchy, and cost center data from Workday (FR-016)."""
    import asyncio

    from app.models.employee import CostCenter, Employee
    from app.models.notification import WorkdaySyncLog
    from app.services.workday import fetch_cost_centers, fetch_employees

    db = _get_sync_session()
    sync_log = WorkdaySyncLog(
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    db.add(sync_log)
    db.commit()

    try:
        # Fetch data from Workday
        cost_centers = asyncio.run(fetch_cost_centers())
        employees = asyncio.run(fetch_employees())

        cc_updated = 0
        emp_updated = 0

        # Upsert cost centers
        for cc_data in cost_centers:
            existing = db.execute(
                select(CostCenter).where(CostCenter.workday_id == cc_data.workday_id)
            ).scalar_one_or_none()

            if existing:
                existing.code = cc_data.code
                existing.name = cc_data.name
            else:
                db.add(CostCenter(
                    workday_id=cc_data.workday_id,
                    code=cc_data.code,
                    name=cc_data.name,
                ))
            cc_updated += 1

        db.flush()

        # Upsert employees (two-pass to handle manager references)
        email_to_id: dict[str, str] = {}
        for emp_data in employees:
            existing = db.execute(
                select(Employee).where(Employee.email == emp_data.email)
            ).scalar_one_or_none()

            if existing:
                existing.full_name = emp_data.full_name
                existing.workday_synced_at = datetime.now(timezone.utc)
                email_to_id[emp_data.email] = str(existing.id)
            else:
                new_emp = Employee(
                    entra_oid=emp_data.workday_id,  # Will be updated on first login
                    email=emp_data.email,
                    full_name=emp_data.full_name,
                    workday_synced_at=datetime.now(timezone.utc),
                )
                db.add(new_emp)
                db.flush()
                email_to_id[emp_data.email] = str(new_emp.id)
            emp_updated += 1

        # Second pass: set manager relationships
        for emp_data in employees:
            if emp_data.manager_workday_id:
                emp = db.execute(
                    select(Employee).where(Employee.email == emp_data.email)
                ).scalar_one_or_none()
                manager = db.execute(
                    select(Employee).where(Employee.entra_oid == emp_data.manager_workday_id)
                ).scalar_one_or_none()
                if emp and manager:
                    emp.manager_id = manager.id

            # Set cost center
            if emp_data.cost_center_code:
                emp = db.execute(
                    select(Employee).where(Employee.email == emp_data.email)
                ).scalar_one_or_none()
                cc = db.execute(
                    select(CostCenter).where(CostCenter.code == emp_data.cost_center_code)
                ).scalar_one_or_none()
                if emp and cc:
                    emp.cost_center_id = cc.id

        sync_log.status = "success"
        sync_log.completed_at = datetime.now(timezone.utc)
        sync_log.employees_updated = emp_updated
        sync_log.cost_centers_updated = cc_updated
        db.commit()

        logger.info(
            "workday_sync_complete",
            employees=emp_updated,
            cost_centers=cc_updated,
        )
        return {"status": "success", "employees": emp_updated, "cost_centers": cc_updated}

    except Exception as exc:
        db.rollback()
        sync_log.status = "failed"
        sync_log.completed_at = datetime.now(timezone.utc)
        sync_log.error_details = str(exc)
        db.add(sync_log)
        db.commit()
        logger.exception("workday_sync_failed")
        raise
    finally:
        db.close()


@shared_task(name="app.tasks.scheduled_tasks.check_stale_approvals", queue="scheduled")
def check_stale_approvals() -> dict:
    """Escalate reports pending approval for more than N business days (FR-011)."""
    import asyncio

    from app.core.approval_workflow import escalate_report
    from app.models.expense import ExpenseReport
    from app.models.policy import ApprovalThreshold

    db = _get_sync_session()
    try:
        # Get escalation threshold
        threshold = db.execute(select(ApprovalThreshold).limit(1)).scalar_one_or_none()
        escalation_days = threshold.auto_escalation_business_days if threshold else 5

        # Calculate the cutoff date (approximate business days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=escalation_days * 1.5)

        # Find stale reports
        stale_reports = db.execute(
            select(ExpenseReport)
            .options(selectinload(ExpenseReport.line_items))
            .where(
                and_(
                    ExpenseReport.status == "submitted",
                    ExpenseReport.current_approver_id.isnot(None),
                    ExpenseReport.submitted_at <= cutoff,
                    ExpenseReport.is_deleted.is_(False),
                )
            )
        ).scalars().all()

        escalated = 0
        for report in stale_reports:
            # Use async escalation in sync context
            from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

            async_engine = create_async_engine(settings.database_url)
            async_factory = async_sessionmaker(async_engine, expire_on_commit=False)

            async def _escalate() -> bool:
                async with async_factory() as async_db:
                    # Reload report in async context
                    r = (await async_db.execute(
                        select(ExpenseReport)
                        .options(selectinload(ExpenseReport.line_items))
                        .where(ExpenseReport.id == report.id)
                    )).scalar_one()
                    result = await escalate_report(async_db, r)
                    await async_db.commit()
                    return result is not None

            if asyncio.run(_escalate()):
                escalated += 1

        logger.info("stale_approval_check", stale_found=len(stale_reports), escalated=escalated)
        return {"stale_found": len(stale_reports), "escalated": escalated}

    except Exception:
        logger.exception("stale_approval_check_failed")
        raise
    finally:
        db.close()


@shared_task(name="app.tasks.scheduled_tasks.send_approval_reminders", queue="scheduled")
def send_approval_reminders() -> dict:
    """Send reminders for reports pending approval for 3+ business days (FR-023)."""
    from app.models.employee import Employee
    from app.models.expense import ExpenseReport
    from app.models.policy import ApprovalThreshold
    from app.services.email import send_email

    db = _get_sync_session()
    try:
        threshold = db.execute(select(ApprovalThreshold).limit(1)).scalar_one_or_none()
        reminder_days = threshold.reminder_business_days if threshold else 3

        # Approximate business days
        cutoff = datetime.now(timezone.utc) - timedelta(days=reminder_days * 1.5)

        pending_reports = db.execute(
            select(ExpenseReport)
            .options(selectinload(ExpenseReport.submitter))
            .where(
                and_(
                    ExpenseReport.status.in_(["submitted", "finance_review"]),
                    ExpenseReport.current_approver_id.isnot(None),
                    ExpenseReport.submitted_at <= cutoff,
                    ExpenseReport.is_deleted.is_(False),
                )
            )
        ).scalars().all()

        reminders_sent = 0
        for report in pending_reports:
            approver = db.execute(
                select(Employee).where(Employee.id == report.current_approver_id)
            ).scalar_one_or_none()

            if approver:
                subject = f"Reminder: Expense Report Pending Your Approval — {report.title}"
                body = (
                    f"<p>Expense report <strong>{report.report_number}</strong> from "
                    f"{report.submitter.full_name} has been pending your approval since "
                    f"{report.submitted_at.strftime('%b %d, %Y') if report.submitted_at else 'unknown'}.</p>"
                    f'<p><a href="{settings.base_url}/approvals/{report.id}">Review Now</a></p>'
                )
                try:
                    send_email(approver.email, subject, body)
                    reminders_sent += 1
                except Exception:
                    logger.exception("reminder_send_failed", report_id=str(report.id))

        db.commit()
        logger.info("approval_reminders_sent", count=reminders_sent)
        return {"reminders_sent": reminders_sent}

    except Exception:
        db.rollback()
        logger.exception("approval_reminders_failed")
        raise
    finally:
        db.close()
