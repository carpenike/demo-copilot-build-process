"""Azure AI Search client wrapper for vector and hybrid search operations."""

from dataclasses import dataclass

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
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
from azure.search.documents.models import VectorizedQuery

from app.config import Settings


@dataclass
class SearchResult:
    """A single search result from Azure AI Search."""

    document_id: str
    version_id: str
    chunk_index: int
    content: str
    section_heading: str | None
    document_title: str
    category: str
    effective_date: str | None
    source_url: str | None
    score: float


class SearchService:
    """Wraps Azure AI Search for index management and hybrid queries."""

    def __init__(self, settings: Settings) -> None:
        credential = DefaultAzureCredential()
        self._search_client = SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=settings.azure_search_index_name,
            credential=credential,
        )
        self._index_client = SearchIndexClient(
            endpoint=settings.azure_search_endpoint,
            credential=credential,
        )
        self._index_name = settings.azure_search_index_name
        self._embedding_dimensions = settings.azure_openai_embedding_dimensions

    async def hybrid_search(
        self,
        query_text: str,
        query_vector: list[float],
        *,
        top_k: int = 5,
        category_filter: str | None = None,
    ) -> list[SearchResult]:
        """Execute hybrid search combining vector similarity and BM25 keyword matching."""
        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top_k,
            fields="content_vector",
        )

        filter_expression = f"category eq '{category_filter}'" if category_filter else None

        results = self._search_client.search(
            search_text=query_text,
            vector_queries=[vector_query],
            filter=filter_expression,
            top=top_k,
            query_type="semantic",
            semantic_configuration_name="policy-semantic-config",
        )

        search_results: list[SearchResult] = []
        for result in results:
            search_results.append(
                SearchResult(
                    document_id=result["document_id"],
                    version_id=result["version_id"],
                    chunk_index=result["chunk_index"],
                    content=result["content"],
                    section_heading=result.get("section_heading"),
                    document_title=result["document_title"],
                    category=result["category"],
                    effective_date=result.get("effective_date"),
                    source_url=result.get("source_url"),
                    score=result["@search.score"],
                )
            )

        return search_results

    async def keyword_search(
        self,
        query_text: str,
        *,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """BM25 keyword-only fallback search when LLM is unavailable (NFR-006)."""
        results = self._search_client.search(
            search_text=query_text,
            top=top_k,
        )

        search_results: list[SearchResult] = []
        for result in results:
            search_results.append(
                SearchResult(
                    document_id=result["document_id"],
                    version_id=result["version_id"],
                    chunk_index=result["chunk_index"],
                    content=result["content"],
                    section_heading=result.get("section_heading"),
                    document_title=result["document_title"],
                    category=result["category"],
                    effective_date=result.get("effective_date"),
                    source_url=result.get("source_url"),
                    score=result["@search.score"],
                )
            )

        return search_results

    async def upload_chunks(self, documents: list[dict]) -> None:  # type: ignore[type-arg]
        """Upload document chunks with embeddings to the search index."""
        self._search_client.upload_documents(documents=documents)

    async def delete_by_version(self, version_id: str) -> None:
        """Remove all chunks for a specific document version from the index."""
        results = self._search_client.search(
            search_text="*",
            filter=f"version_id eq '{version_id}'",
            select=["id"],
        )
        doc_ids = [{"id": r["id"]} for r in results]
        if doc_ids:
            self._search_client.delete_documents(documents=doc_ids)

    def ensure_index(self) -> None:
        """Create or update the search index with the required schema."""
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="version_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, sortable=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchableField(
                name="section_heading",
                type=SearchFieldDataType.String,
                filterable=True,
            ),
            SearchableField(
                name="document_title",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SimpleField(
                name="category",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SimpleField(
                name="effective_date",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True,
            ),
            SimpleField(name="source_url", type=SearchFieldDataType.String),
            SimpleField(name="owner", type=SearchFieldDataType.String, filterable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self._embedding_dimensions,
                vector_search_profile_name="policy-vector-profile",
            ),
        ]

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(name="policy-hnsw"),
            ],
            profiles=[
                VectorSearchProfile(
                    name="policy-vector-profile",
                    algorithm_configuration_name="policy-hnsw",
                ),
            ],
        )

        semantic_config = SemanticConfiguration(
            name="policy-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="content")],
                title_field=SemanticField(field_name="document_title"),
            ),
        )

        index = SearchIndex(
            name=self._index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=SemanticSearch(configurations=[semantic_config]),
        )

        self._index_client.create_or_update_index(index)
