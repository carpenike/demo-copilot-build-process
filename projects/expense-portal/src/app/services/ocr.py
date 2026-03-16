"""Azure AI Document Intelligence client for receipt OCR (ADR-0006)."""

from dataclasses import dataclass
from decimal import Decimal

import structlog
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class OcrField:
    value: str | float | None
    confidence: float


@dataclass
class OcrResult:
    amount: OcrField | None = None
    vendor_name: OcrField | None = None
    date: OcrField | None = None


def extract_receipt_fields(file_content: bytes, content_type: str) -> OcrResult:
    """Call Azure Document Intelligence prebuilt receipt model and return extracted fields."""
    client = DocumentIntelligenceClient(
        endpoint=settings.docai_endpoint,
        credential=AzureKeyCredential(settings.docai_key),
    )

    poller = client.begin_analyze_document(
        model_id="prebuilt-receipt",
        body=file_content,
        content_type=content_type,
    )
    result = poller.result()

    ocr = OcrResult()
    if not result.documents:
        logger.warning("ocr_no_documents_found")
        return ocr

    doc = result.documents[0]
    fields = doc.fields or {}

    if "Total" in fields:
        total_field = fields["Total"]
        ocr.amount = OcrField(
            value=total_field.value,
            confidence=total_field.confidence or 0.0,
        )

    if "MerchantName" in fields:
        merchant_field = fields["MerchantName"]
        ocr.vendor_name = OcrField(
            value=merchant_field.value,
            confidence=merchant_field.confidence or 0.0,
        )

    if "TransactionDate" in fields:
        date_field = fields["TransactionDate"]
        date_value = date_field.value
        if hasattr(date_value, "isoformat"):
            date_value = date_value.isoformat()
        ocr.date = OcrField(
            value=str(date_value) if date_value else None,
            confidence=date_field.confidence or 0.0,
        )

    logger.info(
        "ocr_extraction_complete",
        has_amount=ocr.amount is not None,
        has_vendor=ocr.vendor_name is not None,
        has_date=ocr.date is not None,
    )
    return ocr


def filter_by_confidence(ocr: OcrResult, threshold: float) -> dict:
    """Return only fields that meet the confidence threshold (FR-004).

    Returns a dict suitable for storing as ocr_results JSONB.
    """
    result: dict = {}
    for field_name, field in [("amount", ocr.amount), ("vendor_name", ocr.vendor_name), ("date", ocr.date)]:
        if field and field.confidence >= threshold:
            result[field_name] = {"value": field.value, "confidence": field.confidence}
    return result
