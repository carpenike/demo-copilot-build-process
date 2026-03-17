"""Azure AI Search service for hybrid vector + keyword retrieval.

Manages the search index schema and provides query methods for the RAG
pipeline. Uses lazy SDK imports so the module can be imported in CI
environments without Azure credentials.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from app.config import Settings

logger = structlog.get_logger()

# Azure AI Search index field definitions
INDEX_FIELDS_SCHEMA: list[dict[str, Any]] = [
    {"name": "chunk_id", "type": "Edm.String", "key": True, "filterable": True},
    {"name": "document_id", "type": "Edm.String", "filterable": True},
    {"name": "content", "type": "Edm.String", "searchable": True},
    {"name": "title", "type": "Edm.String", "searchable": True, "filterable": True},
    {"name": "section_heading", "type": "Edm.String", "searchable": True, "filterable": True},
    {"name": "category", "type": "Edm.String", "filterable": True},
    {"name": "effective_date", "type": "Edm.DateTimeOffset", "filterable": True},
    {"name": "source_url", "type": "Edm.String"},
    {"name": "page_number", "type": "Edm.Int32", "filterable": True},
]


class SearchService:
    """Manages Azure AI Search operations for document retrieval."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._search_client: Any = None
        self._index_client: Any = None

    def _get_credential(self) -> Any:
        """Create Azure credential using DefaultAzureCredential."""
        from azure.identity import DefaultAzureCredential

        return DefaultAzureCredential()

    def _get_search_client(self) -> Any:
        """Lazily initialize the search client."""
        if self._search_client is None:
            from azure.search.documents import SearchClient

            self._search_client = SearchClient(
                endpoint=self._settings.azure_search_endpoint,
                index_name=self._settings.azure_search_index_name,
                credential=self._get_credential(),
            )
        return self._search_client

    def _get_index_client(self) -> Any:
        """Lazily initialize the index management client."""
        if self._index_client is None:
            from azure.search.documents.indexes import SearchIndexClient

            self._index_client = SearchIndexClient(
                endpoint=self._settings.azure_search_endpoint,
                credential=self._get_credential(),
            )
        return self._index_client

    async def ensure_index(self) -> None:
        """Create the search index if it does not already exist.

        Called during FastAPI lifespan startup so the index is ready on
        first deploy without manual steps.
        """
        from azure.search.documents.indexes.models import (
            HnswAlgorithmConfiguration,
            SearchableField,
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            SemanticConfiguration,
            SemanticField,
            SemanticPrioritizedFields,
            SemanticSearch,
            SimpleField,
            VectorSearch,
            VectorSearchProfile,
        )

        index_name = self._settings.azure_search_index_name
        client = self._get_index_client()

        existing_names = [idx.name for idx in client.list_indexes()]
        if index_name in existing_names:
            logger.info("search_index_exists", index_name=index_name)
            return

        fields = [
            SimpleField(
                name="chunk_id", type=SearchFieldDataType.String, key=True, filterable=True
            ),
            SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self._settings.azure_openai_embedding_dimensions,
                vector_search_profile_name="default-vector-profile",
            ),
            SearchableField(name="title", type=SearchFieldDataType.String, filterable=True),
            SearchableField(
                name="section_heading", type=SearchFieldDataType.String, filterable=True
            ),
            SimpleField(name="category", type=SearchFieldDataType.String, filterable=True),
            SimpleField(
                name="effective_date", type=SearchFieldDataType.DateTimeOffset, filterable=True
            ),
            SimpleField(name="source_url", type=SearchFieldDataType.String),
            SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
        ]

        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="default-hnsw")],
            profiles=[
                VectorSearchProfile(
                    name="default-vector-profile", algorithm_configuration_name="default-hnsw"
                )
            ],
        )

        semantic_config = SemanticConfiguration(
            name="default-semantic",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="content")]
            ),
        )

        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=SemanticSearch(configurations=[semantic_config]),
        )

        client.create_index(index)
        logger.info("search_index_created", index_name=index_name)

    async def hybrid_search(
        self,
        query_text: str,
        query_vector: list[float],
        top_k: int = 5,
        category_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a hybrid (vector + keyword) search with semantic ranking.

        Returns the top-k document chunks with metadata for the RAG pipeline.
        """
        from azure.search.documents.models import VectorizedQuery

        client = self._get_search_client()

        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top_k,
            fields="content_vector",
        )

        filter_expr = f"category eq '{category_filter}'" if category_filter else None

        results = client.search(
            search_text=query_text,
            vector_queries=[vector_query],
            filter=filter_expr,
            query_type="semantic",
            semantic_configuration_name="default-semantic",
            top=top_k,
            select=[
                "chunk_id",
                "document_id",
                "content",
                "title",
                "section_heading",
                "category",
                "effective_date",
                "source_url",
                "page_number",
            ],
        )

        chunks: list[dict[str, Any]] = []
        for result in results:
            chunks.append(
                {
                    "chunk_id": result["chunk_id"],
                    "document_id": result["document_id"],
                    "content": result["content"],
                    "title": result["title"],
                    "section_heading": result.get("section_heading", ""),
                    "category": result.get("category", ""),
                    "effective_date": result.get("effective_date", ""),
                    "source_url": result.get("source_url", ""),
                    "page_number": result.get("page_number"),
                    "score": result.get("@search.score", 0.0),
                    "reranker_score": result.get("@search.reranker_score", 0.0),
                }
            )

        return chunks

    async def upsert_chunks(self, documents: list[dict[str, Any]]) -> None:
        """Upload or update document chunks in the search index."""
        client = self._get_search_client()
        client.upload_documents(documents=documents)
        logger.info("chunks_upserted", count=len(documents))

    async def delete_document_chunks(self, document_id: str) -> None:
        """Remove all chunks for a specific document from the search index."""
        client = self._get_search_client()

        results = client.search(
            search_text="*",
            filter=f"document_id eq '{document_id}'",
            select=["chunk_id"],
        )

        chunk_ids = [{"chunk_id": r["chunk_id"]} for r in results]
        if chunk_ids:
            client.delete_documents(documents=chunk_ids)
            logger.info("chunks_deleted", document_id=document_id, count=len(chunk_ids))

    async def keyword_search(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Keyword-only fallback search when LLM is unavailable (NFR-006)."""
        client = self._get_search_client()

        results = client.search(
            search_text=query_text,
            top=top_k,
            select=[
                "chunk_id",
                "document_id",
                "content",
                "title",
                "section_heading",
                "category",
                "effective_date",
                "source_url",
            ],
        )

        return [
            {
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "content": r["content"],
                "title": r["title"],
                "section_heading": r.get("section_heading", ""),
                "source_url": r.get("source_url", ""),
            }
            for r in results
        ]

    async def check_health(self) -> bool:
        """Check if Azure AI Search is reachable."""
        try:
            client = self._get_index_client()
            list(client.list_indexes())
        except Exception:
            logger.warning("ai_search_health_check_failed")
            return False
        else:
            return True

    def generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate a deterministic chunk ID for the search index."""
        return f"{document_id}_{chunk_index}_{uuid.uuid4().hex[:8]}"
