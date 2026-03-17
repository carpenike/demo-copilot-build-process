# ADR-0009: Policy Chatbot — Data Storage

> **Status:** Proposed
> **Date:** 2026-03-17
> **Deciders:** Platform Engineering
> **Project:** policy-chatbot

---

## Context

The policy-chatbot system requires several categories of data storage:

1. **Vector store** — storing document chunk embeddings for semantic retrieval
   (FR-003, FR-012). Must support vector similarity search at scale (NFR-014:
   500 documents, 30,000 pages).
2. **Relational database** — storing document metadata, conversation history,
   feedback, analytics, and admin state (FR-004, FR-006, FR-028, FR-029, FR-030).
3. **Blob storage** — storing raw uploaded policy document files (FR-001, FR-031).
4. **Cache / message broker** — Celery task queue for background processing and
   optional response caching (NFR-001, NFR-005).

The enterprise standard (ADR-0002) establishes Azure Database for PostgreSQL as
the standard relational store. The Cloud Service Preference Policy requires
Azure PaaS services for all storage needs.

---

## Decision

> We will use the following Azure PaaS data services:
>
> | Need | Service |
> |------|---------|
> | Vector search | **Azure AI Search** (integrated vectorization) |
> | Relational data | **Azure Database for PostgreSQL Flexible Server** |
> | Blob storage | **Azure Blob Storage** |
> | Cache + message broker | **Azure Cache for Redis** |

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Data storage | Azure PaaS-first | All Azure PaaS services | ✅ |
| Relational DB | PostgreSQL (ADR-0002) | Azure DB for PostgreSQL Flexible Server | ✅ |
| Secrets | Azure Key Vault | Connection strings via Key Vault | ✅ |
| IaC | Bicep | All resources provisioned via Bicep | ✅ |

---

## Options Considered

### Vector Search

#### Option A: Azure AI Search ← Chosen

**Description:** Azure AI Search with integrated vector search, supporting both
keyword and vector queries (hybrid search). Embeddings generated via Azure OpenAI
and stored in AI Search indexes.

**Pros:**
- Azure PaaS — fully managed, no infrastructure to operate
- Native vector search with HNSW indexing
- Hybrid search (keyword + vector) improves retrieval quality for RAG
- Integrated with Azure OpenAI for embedding generation
- Supports semantic ranking for re-ranking retrieved chunks
- Built-in document cracking for PDF/DOCX (Azure AI Document Intelligence)
- Scales to millions of documents (NFR-014 easily met)
- SDK: `azure-search-documents` Python package

**Cons:**
- Additional Azure service cost vs. self-hosted vector DB
- Index schema changes require re-indexing

#### Option B: PostgreSQL pgvector extension

**Description:** Use pgvector extension in Azure Database for PostgreSQL for
vector storage alongside relational data.

**Pros:**
- Single data store — reduces infrastructure components
- No additional service cost

**Cons:**
- pgvector performance degrades at scale compared to purpose-built vector search
- No hybrid search (keyword + vector) without additional custom code
- No semantic re-ranking — must build ranking logic from scratch
- Missing document cracking/chunking features that AI Search provides out of box
- Would require building the entire retrieval pipeline from scratch

#### Option C: Self-hosted Qdrant / Weaviate / Pinecone

**Cons:**
- Third-party / self-managed — violates Azure PaaS-first policy
- Additional operational burden
- Pinecone is an external SaaS — data residency concerns

### Relational Database

Inherits ADR-0002: **Azure Database for PostgreSQL Flexible Server**. No
alternatives considered — this is the platform standard.

### Blob Storage

**Azure Blob Storage** is the only Azure PaaS option for object/file storage.
No alternatives considered.

### Cache / Message Broker

#### Option A: Azure Cache for Redis ← Chosen

**Description:** Managed Redis for Celery task queue and optional response caching.

**Pros:**
- Azure PaaS — fully managed
- Celery natively supports Redis as broker and result backend
- Can also serve as a session cache for conversation context (FR-009)
- Supports pub/sub for real-time notifications if needed in v2

**Cons:**
- Additional service cost

#### Option B: Azure Service Bus

**Pros:**
- Enterprise message broker with guaranteed delivery

**Cons:**
- Celery does not have a mature Azure Service Bus transport
- Overkill for the task queue use case — Redis is simpler and Celery-native

---

## Consequences

### Positive
- All storage is Azure PaaS — zero self-managed infrastructure
- Azure AI Search provides a complete RAG retrieval solution (vectorization,
  hybrid search, semantic ranking, document cracking)
- PostgreSQL handles all relational needs (metadata, conversations, feedback,
  analytics) with a proven platform standard
- Redis serves dual purpose: Celery broker + conversation session cache

### Negative / Trade-offs
- Four distinct Azure services to provision and manage (AI Search, PostgreSQL,
  Blob Storage, Redis)
- Azure AI Search adds cost beyond PostgreSQL — justified by superior retrieval
  quality for RAG workloads
- Must keep document metadata in sync between PostgreSQL (source of truth) and
  AI Search index (search index)

### Risks
- Azure AI Search index schema changes require re-indexing (mitigated by
  designing the schema carefully upfront)
- Redis as single message broker — if Redis is unavailable, Celery workers stall
  (mitigated by Azure Cache for Redis SLA: 99.9%)

---

## Implementation Notes

### Azure AI Search
- Index name: `policy-documents`
- Fields: `chunk_id`, `document_id`, `content`, `content_vector` (embedding),
  `title`, `section_heading`, `category`, `effective_date`, `source_url`
- Vector config: HNSW algorithm, 1536 dimensions (text-embedding-ada-002) or
  3072 dimensions (text-embedding-3-large)
- Hybrid search: combine vector similarity + BM25 keyword scoring
- Semantic ranker enabled for re-ranking top results

### Azure Database for PostgreSQL
- Tables: `documents`, `document_versions`, `conversations`, `messages`,
  `feedback`, `analytics_events`, `admin_users`
- Alembic for schema migrations
- SQLAlchemy as ORM

### Azure Blob Storage
- Container: `policy-documents` for raw uploaded files
- Container: `processed-documents` for extracted/chunked text (intermediate)
- Managed identity access — no storage account keys in config

### Azure Cache for Redis
- Used as Celery broker (`redis://`) and result backend
- Optional: conversation session storage with TTL for FR-009
- Managed identity or access key via Key Vault

---

## References
- ADR-0002: Platform Data Storage Strategy
- Governance: `governance/enterprise-standards.md` § Cloud Service Preference Policy
- Requirements: FR-001–FR-006, FR-009, FR-012, FR-028–FR-030, NFR-014
