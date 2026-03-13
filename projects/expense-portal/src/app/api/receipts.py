"""Receipt upload and OCR status endpoints."""

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.models.database import get_db
from app.models.employee import Employee
from app.models.expense import ExpenseReport, LineItem, Receipt
from app.models.schemas import OcrStatusOut, ReceiptUploadOut
from app.services.blob_storage import generate_receipt_sas_url, upload_receipt

logger = structlog.get_logger()
router = APIRouter(prefix="/v1", tags=["receipts"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/expenses/reports/{report_id}/line-items/{item_id}/receipt",
    response_model=ReceiptUploadOut,
    status_code=202,
)
async def upload_receipt_file(
    report_id: uuid.UUID,
    item_id: uuid.UUID,
    file: UploadFile,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> ReceiptUploadOut:
    """Upload a receipt image for a line item. Triggers async OCR."""
    # Validate report ownership and editability
    result = await db.execute(
        select(ExpenseReport).where(
            ExpenseReport.id == report_id, ExpenseReport.is_deleted.is_(False)
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.submitter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the owner of this report")
    if not report.is_editable:
        raise HTTPException(status_code=409, detail="Report is not editable")

    # Validate line item exists
    item_result = await db.execute(
        select(LineItem).where(LineItem.id == item_id, LineItem.report_id == report_id)
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")

    # Validate file
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use JPEG, PNG, or PDF.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10 MB limit")

    # Upload to blob storage
    blob_path = await upload_receipt(
        file_content=content,
        original_filename=file.filename or "receipt",
        content_type=file.content_type,
        report_id=report_id,
        line_item_id=item_id,
    )

    # Create receipt record
    receipt = Receipt(
        line_item_id=item_id,
        blob_path=blob_path,
        original_filename=file.filename or "receipt",
        content_type=file.content_type,
        file_size_bytes=len(content),
    )
    db.add(receipt)
    item.ocr_status = "processing"
    await db.flush()

    # Queue OCR task
    from app.tasks.ocr_tasks import process_receipt_ocr

    task = process_receipt_ocr.delay(str(receipt.id))
    receipt.ocr_task_id = task.id
    await db.flush()

    return ReceiptUploadOut(
        receipt_url=f"/v1/receipts/{receipt.id}",
        ocr_status="processing",
        ocr_task_id=task.id,
    )


@router.get("/receipts/{receipt_id}")
async def get_receipt(
    receipt_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> RedirectResponse:
    """Download a receipt — redirects to a time-limited SAS URL."""
    result = await db.execute(
        select(Receipt)
        .options(selectinload(Receipt.line_item).selectinload(LineItem.report))
        .where(Receipt.id == receipt_id)
    )
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # Permission check
    report = receipt.line_item.report
    is_owner = report.submitter_id == current_user.id
    is_manager = report.submitter_id in {dr.id for dr in current_user.direct_reports}
    if not (is_owner or is_manager or current_user.is_finance_reviewer):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    sas_url = generate_receipt_sas_url(receipt.blob_path)
    return RedirectResponse(url=sas_url, status_code=302)


@router.get("/expenses/ocr-status/{task_id}", response_model=OcrStatusOut)
async def get_ocr_status(
    task_id: str,
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> OcrStatusOut:
    """Poll OCR processing status for a receipt."""
    from app.tasks.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)

    if result.state == "PENDING":
        return OcrStatusOut(task_id=task_id, status="processing")
    elif result.state == "SUCCESS":
        return OcrStatusOut(
            task_id=task_id,
            status="completed",
            extracted_fields=result.result,
        )
    elif result.state == "FAILURE":
        return OcrStatusOut(task_id=task_id, status="failed")
    else:
        return OcrStatusOut(task_id=task_id, status="processing")
