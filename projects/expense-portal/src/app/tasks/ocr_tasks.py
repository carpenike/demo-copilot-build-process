"""OCR processing tasks — receipt extraction via Azure Document Intelligence (ADR-0006)."""

import structlog
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.blob_storage import download_receipt
from app.services.ocr import extract_receipt_fields, filter_by_confidence

logger = structlog.get_logger()
settings = get_settings()


def _get_sync_session() -> Session:
    """Create a synchronous DB session for Celery workers."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url)
    return sessionmaker(bind=engine)()


@shared_task(
    bind=True,
    name="app.tasks.ocr_tasks.process_receipt_ocr",
    queue="ocr",
    max_retries=3,
    default_retry_delay=30,
)
def process_receipt_ocr(self, receipt_id: str) -> dict | None:  # type: ignore[no-untyped-def]
    """Process a receipt image through Azure Document Intelligence.

    Downloads the receipt from Blob Storage, extracts fields, and updates
    the line item with pre-filled values where confidence >= threshold.
    """
    from app.models.expense import LineItem, Receipt

    db = _get_sync_session()
    try:
        receipt = db.execute(
            select(Receipt).where(Receipt.id == receipt_id)
        ).scalar_one_or_none()

        if not receipt:
            logger.error("ocr_receipt_not_found", receipt_id=receipt_id)
            return None

        # Download from Blob Storage
        import asyncio
        file_content = asyncio.run(download_receipt(receipt.blob_path))

        # Run OCR extraction
        ocr_result = extract_receipt_fields(file_content, receipt.content_type)

        # Filter by confidence threshold
        filtered = filter_by_confidence(ocr_result, settings.ocr_confidence_threshold)

        # Update receipt with OCR results
        receipt.ocr_results = filtered

        # Update line item OCR status
        line_item = db.execute(
            select(LineItem).where(LineItem.id == receipt.line_item_id)
        ).scalar_one_or_none()

        if line_item:
            line_item.ocr_status = "completed"

        db.commit()
        logger.info("ocr_complete", receipt_id=receipt_id, fields_extracted=len(filtered))
        return filtered

    except Exception as exc:
        db.rollback()
        logger.exception("ocr_failed", receipt_id=receipt_id)
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        db.close()
