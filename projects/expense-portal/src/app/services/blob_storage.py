"""Azure Blob Storage client for receipt images (ADR-0005)."""

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


def _get_blob_service_client() -> BlobServiceClient:
    credential = DefaultAzureCredential()
    return BlobServiceClient(account_url=settings.blob_account_url, credential=credential)


async def upload_receipt(
    file_content: bytes,
    original_filename: str,
    content_type: str,
    report_id: uuid.UUID,
    line_item_id: uuid.UUID,
) -> str:
    """Upload a receipt file to Azure Blob Storage. Returns the blob path."""
    blob_path = f"{report_id}/{line_item_id}/{uuid.uuid4()}-{original_filename}"
    client = _get_blob_service_client()
    container_client = client.get_container_client(settings.blob_container_name)
    blob_client = container_client.get_blob_client(blob_path)

    blob_client.upload_blob(
        file_content,
        content_type=content_type,
        overwrite=True,
    )
    logger.info("receipt_uploaded", blob_path=blob_path, size=len(file_content))
    return blob_path


def generate_receipt_sas_url(blob_path: str, expiry_minutes: int = 15) -> str:
    """Generate a time-limited SAS URL for downloading a receipt."""
    client = _get_blob_service_client()
    user_delegation_key = client.get_user_delegation_key(
        key_start_time=datetime.now(timezone.utc),
        key_expiry_time=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
    )

    sas_token = generate_blob_sas(
        account_name=client.account_name,
        container_name=settings.blob_container_name,
        blob_name=blob_path,
        user_delegation_key=user_delegation_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
    )
    return f"{settings.blob_account_url}/{settings.blob_container_name}/{blob_path}?{sas_token}"


async def download_receipt(blob_path: str) -> bytes:
    """Download a receipt file from blob storage for OCR processing."""
    client = _get_blob_service_client()
    container_client = client.get_container_client(settings.blob_container_name)
    blob_client = container_client.get_blob_client(blob_path)
    return blob_client.download_blob().readall()
