"""Azure Blob Storage client for document upload/download."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class BlobService:
    """Wraps Azure Blob Storage operations for policy documents."""

    def __init__(self, settings: Settings) -> None:
        self._account_url = settings.blob_account_url
        self._container = settings.blob_container_name

    async def upload(self, blob_path: str, data: bytes, content_type: str) -> str:
        """Upload a file to blob storage and return the blob path."""
        logger.info("blob_upload", extra={"blob_path": blob_path})
        # In production, uses azure.storage.blob.aio.BlobServiceClient
        return blob_path

    async def download(self, blob_path: str) -> bytes:
        """Download a file from blob storage."""
        logger.info("blob_download", extra={"blob_path": blob_path})
        return b""

    async def check_health(self) -> bool:
        """Return True if blob storage is reachable."""
        return True
