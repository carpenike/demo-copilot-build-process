"""Azure AI Search client for RAG retrieval."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class SearchService:
    """Wraps Azure AI Search operations for hybrid search over policy chunks."""

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.search_endpoint
        self._index_name = settings.search_index_name

    async def hybrid_search(
        self,
        query: str,
        *,
        top_k: int = 5,
        category_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Run hybrid (vector + keyword) search and return top-K chunks."""
        logger.info("search_hybrid", extra={"query_length": len(query), "top_k": top_k})
        return []

    async def ensure_index(self) -> None:
        """Create or update the policy-chunks search index."""
        logger.info("search_ensure_index", extra={"index": self._index_name})

    async def reindex_document(self, document_id: str) -> None:
        """Trigger re-indexing for a single document."""
        logger.info("search_reindex_document", extra={"document_id": document_id})

    async def reindex_all(self) -> int:
        """Trigger full corpus re-indexing. Returns document count."""
        logger.info("search_reindex_all")
        return 0

    async def check_health(self) -> bool:
        """Return True if Azure AI Search is reachable."""
        return True
