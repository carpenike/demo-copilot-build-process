"""SAP integration tasks — payment batch generation and GL journal entries (FR-017, FR-018)."""

from decimal import Decimal

import structlog
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.services.sap import PaymentBatchItem, generate_idoc_batch, transmit_to_sap, write_gl_journal_entry

logger = structlog.get_logger()
settings = get_settings()


def _get_sync_session() -> Session:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url)
    return sessionmaker(bind=engine)()


@shared_task(
    bind=True,
    name="app.tasks.integration_tasks.process_payment",
    queue="integrations",
    max_retries=5,
    default_retry_delay=60,
)
def process_payment(self, report_id: str) -> None:  # type: ignore[no-untyped-def]
    """Generate SAP IDoc payment batch and GL journal entry for an approved report."""
    from app.models.employee import Employee
    from app.models.expense import ExpenseReport, LineItem

    db = _get_sync_session()
    try:
        report = db.execute(
            select(ExpenseReport)
            .options(
                selectinload(ExpenseReport.line_items),
                selectinload(ExpenseReport.submitter).selectinload(Employee.cost_center),
            )
            .where(ExpenseReport.id == report_id)
        ).scalar_one_or_none()

        if not report:
            logger.error("payment_report_not_found", report_id=report_id)
            return

        if report.status != "approved":
            logger.warning("payment_invalid_status", report_id=report_id, status=report.status)
            return

        submitter = report.submitter
        cost_center_code = submitter.cost_center.code if submitter.cost_center else "UNKNOWN"

        # Build batch items
        batch_items = [
            PaymentBatchItem(
                report_id=str(report.id),
                employee_email=submitter.email,
                employee_name=submitter.full_name,
                amount=report.total_amount,
                currency=report.currency,
                cost_center_code=cost_center_code,
                gl_account="6100",  # GL account will come from category mapping
            )
        ]

        # Generate IDoc batch (FR-017)
        batch_content = generate_idoc_batch(batch_items)

        # Transmit to SAP
        transmit_to_sap(batch_content)

        # Write GL journal entry (FR-018)
        write_gl_journal_entry(
            report_id=str(report.id),
            amount=report.total_amount,
            currency=report.currency,
            cost_center_code=cost_center_code,
            gl_account="6100",
        )

        # Update report status
        report.status = "payment_processing"
        db.commit()

        logger.info("payment_processed", report_id=report_id, amount=str(report.total_amount))

    except Exception as exc:
        db.rollback()
        logger.exception("payment_failed", report_id=report_id)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
