"""Azure Blob Storage client wrapper for policy document file operations."""

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from app.config import Settings


class BlobService:
    """Wraps Azure Blob Storage for uploading and retrieving raw policy documents."""

    def __init__(self, settings: Settings) -> None:
        credential = DefaultAzureCredential()
        self._blob_service = BlobServiceClient(
            account_url=settings.blob_account_url,
            credential=credential,
        )
        self._container_name = settings.blob_container_name

    async def upload_document(
        self,
        blob_path: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload a document to blob storage and return the blob path."""
        container_client = self._blob_service.get_container_client(self._container_name)
        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(data, content_type=content_type, overwrite=True)
        return blob_path

    async def download_document(self, blob_path: str) -> bytes:
        """Download a document from blob storage by path."""
        container_client = self._blob_service.get_container_client(self._container_name)
        blob_client = container_client.get_blob_client(blob_path)
        stream = blob_client.download_blob()
        return stream.readall()
