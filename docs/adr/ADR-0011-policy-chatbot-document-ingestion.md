# ADR-0011: Policy Chatbot — Document Ingestion Pipeline

> **Status:** Accepted
> **Date:** 2026-03-20
> **Deciders:** Platform Engineering, HR Service Desk Manager
> **Project:** policy-chatbot

---

## Context

The Policy Chatbot must ingest ~140 policy documents (~8,000 pages) from
SharePoint Online, intranet CMS, and Azure Blob Storage (FR-001). Documents
are in PDF, DOCX, and HTML formats (FR-002). The system must preserve section
headings, numbered lists, and table structures during extraction. Single-document
re-indexing must complete within 5 minutes (NFR-002) and full corpus re-indexing
within 2 hours (NFR-003).

Administrators must be able to trigger re-indexing, upload new documents, and
retire outdated documents (FR-005, FR-031). Document version history must be
maintained (FR-006).

---

## Decision

> We will use **Azure Blob Storage** as the canonical document store with
> **Azure AI Search indexers and built-in skillsets** for text extraction and
> chunking, because this minimizes custom code and leverages Azure's native
> document cracking capabilities.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Object storage | Azure PaaS preferred | Azure Blob Storage | ✅ |
| Search indexing | Azure PaaS preferred | Azure AI Search indexer | ✅ |
| Compute (custom processing) | ACA preferred | ACA Job (for metadata sync) | ✅ |
| Secrets | Azure Key Vault | Managed Identity | ✅ |

---

## Options Considered

### Option 1: Blob Storage + AI Search Indexer (built-in skillsets) ← Chosen

**Description:** Upload documents to Blob Storage. Configure an Azure AI Search
indexer with a blob data source. Use built-in cognitive skills for document
cracking (PDF/DOCX/HTML → text), text splitting (chunking), and embedding
generation. The indexer populates the `policy-chunks` search index automatically.

**Pros:**
- Minimal custom code — Azure AI Search handles extraction, chunking, and
  embedding in a declarative pipeline
- Built-in support for PDF, DOCX, HTML, and 20+ other formats
- Incremental indexing — only re-processes changed blobs
- Scheduled or on-demand indexer runs via REST API (admin trigger for FR-005)
- Built-in change detection via blob metadata/timestamps
- Scales to 500+ documents and 30,000+ pages without re-architecture (NFR-014)

**Cons:**
- Less control over chunking algorithm compared to custom code
- Built-in text splitter may not perfectly preserve table structures in all cases
- Debugging indexer failures requires Azure Portal or REST API inspection

---

### Option 2: Custom Python Ingestion Worker (ACA Job)

**Description:** Build a custom Python worker that downloads documents from Blob
Storage, uses `PyMuPDF`/`python-docx`/`BeautifulSoup` for text extraction,
implements custom chunking, generates embeddings via Azure OpenAI, and pushes
chunks to Azure AI Search via the SDK.

**Pros:**
- Full control over extraction, chunking, and preprocessing logic
- Can implement custom table-aware chunking
- Easier to unit test extraction and chunking logic
- Can add custom metadata enrichment during ingestion

**Cons:**
- Significant custom code to build and maintain — extraction, format handling,
  error recovery, progress tracking
- Must handle all document format edge cases (encrypted PDFs, complex DOCX
  layouts, malformed HTML)
- Slower to implement — the AI Search indexer provides this out of the box
- Must build incremental indexing logic manually

---

### Option 3: Azure AI Document Intelligence + Custom Pipeline

**Description:** Use Azure AI Document Intelligence (formerly Form Recognizer)
for high-fidelity document extraction, then a custom pipeline for chunking and
indexing.

**Pros:**
- Superior extraction quality for complex layouts, tables, and forms
- Pre-built models for invoices, receipts, and structured documents

**Cons:**
- Higher per-page cost — Document Intelligence charges per page analyzed
- Over-engineered for text-heavy policy documents that don't have complex forms
- Still requires custom code for chunking and index population
- Adds a third Azure AI service to manage alongside AI Search and OpenAI

---

## Ingestion Pipeline Design

```
┌──────────────┐     ┌───────────────┐     ┌──────────────────────────────┐
│  Admin API   │────▶│  Azure Blob   │────▶│  Azure AI Search Indexer    │
│  (upload)    │     │  Storage      │     │                              │
└──────────────┘     │               │     │  1. Document cracking        │
                     │  policy-      │     │     (PDF/DOCX/HTML → text)   │
┌──────────────┐     │  documents/   │     │  2. Text splitting           │
│  SharePoint  │────▶│               │     │     (512-token chunks,       │
│  Sync Job    │     └───────────────┘     │      50-token overlap)       │
└──────────────┘                           │  3. Embedding generation     │
                                           │     (text-embedding-ada-002) │
                                           │  4. Index population         │
                                           │     (policy-chunks index)    │
                                           └──────────────────────────────┘

┌──────────────┐     ┌───────────────┐
│  Admin API   │────▶│  PostgreSQL   │  ← document metadata, version history
│  (metadata)  │     │  documents    │
└──────────────┘     │  table        │
                     └───────────────┘
```

### Ingestion Flow

1. **Upload:** Admin uploads document via API → stored in Blob Storage
   `policy-documents/{category}/{document_id}/{version}.{ext}`
2. **Metadata:** API writes document metadata to PostgreSQL `documents` table
   (title, category, effective date, owner, source URL, status)
3. **Version tracking:** Previous version marked inactive, new version marked
   active (FR-006)
4. **Indexing trigger:** API calls AI Search indexer run via REST API
5. **Indexer processing:** AI Search indexer detects new/changed blobs,
   extracts text, chunks, generates embeddings, populates search index
6. **Completion:** Indexer status polled by API; admin notified when complete

### SharePoint/Intranet Sync

- An ACA Job (scheduled or manually triggered) pulls documents from SharePoint
  Online and the intranet CMS and uploads them to Blob Storage
- This normalizes all document sources into Blob Storage as the single source
  of truth for the indexer
- v1: manual trigger; v2: scheduled sync (out of scope per requirements)

### Chunking Strategy

- **Chunk size:** 512 tokens (measured by `tiktoken` cl100k_base encoding)
- **Overlap:** 50 tokens between consecutive chunks
- **Section-aware:** AI Search text splitter respects section headings where
  detected, preferring to split at heading boundaries
- **Metadata per chunk:** `document_id`, `document_title`, `section_heading`,
  `category`, `effective_date`, `source_url`, `chunk_index`

---

## Consequences

### Positive
- Leverages Azure-managed infrastructure — no custom extraction code to maintain
- Incremental indexing handles document updates efficiently
- Built-in support for all required document formats (PDF, DOCX, HTML)
- Scales to 500+ documents without architecture changes

### Negative / Trade-offs
- Less control over extraction fidelity — complex tables may lose formatting
- Debugging indexer issues requires Azure Portal access
- Chunking strategy is constrained by AI Search's built-in text splitter
  capabilities

### Risks
- Extraction quality issues with specific PDF layouts — mitigated by UAT
  testing across representative documents and fallback to custom extraction
  for problem documents
- Indexer throughput ceiling for full corpus re-index — mitigated by AI Search
  Standard tier which supports higher throughput

---

## Implementation Notes

- **Blob container:** `policy-documents` (raw files), organized by
  `{category}/{document_id}/{version_id}.{ext}`
- **AI Search data source:** Blob Storage data source pointing to
  `policy-documents` container
- **Skillset:** Built-in document cracking + text split skill +
  Azure OpenAI embedding skill
- **Index:** `policy-chunks` (defined in ADR-0010)
- **Indexer schedule:** On-demand via REST API; no automatic schedule in v1
- **Admin API endpoints:** `POST /v1/admin/documents` (upload),
  `POST /v1/admin/documents/{id}/reindex` (trigger re-index),
  `POST /v1/admin/reindex` (full corpus re-index),
  `PATCH /v1/admin/documents/{id}` (retire/update metadata)
- **SDKs:** `azure-search-documents` (indexer management), `azure-storage-blob`
  (document upload)

---

## References
- [AI Search indexer for Blob Storage](https://learn.microsoft.com/en-us/azure/search/search-howto-indexing-azure-blob-storage)
- [AI Search built-in skills](https://learn.microsoft.com/en-us/azure/search/cognitive-search-predefined-skills)
- [Text split skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-textsplit)
- Related requirements: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-031, NFR-002, NFR-003, NFR-014
- Related ADRs: ADR-0009 (data storage), ADR-0010 (RAG architecture)
