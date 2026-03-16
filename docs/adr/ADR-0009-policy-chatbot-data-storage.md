# ADR-0009: Data Storage — Policy Chatbot

> **Status:** Proposed
> **Date:** 2026-03-16
> **Deciders:** Platform Engineering, HR Service Desk Manager
> **Project:** policy-chatbot

---

## Context

The Policy Chatbot has four distinct data storage needs:

1. **Vector store** — store document chunk embeddings for semantic retrieval
   (FR-003, FR-012). Must support hybrid search (vector + keyword) for the
   LLM fallback mode (NFR-006). Must scale to 500 documents / 30,000 pages
   (NFR-014).
2. **Relational data** — store document metadata, conversation logs, feedback,
   analytics aggregations, user sessions, and admin configuration (FR-004,
   FR-006, FR-028, FR-029, FR-030, FR-033, NFR-008).
3. **Session/cache store** — maintain conversation context within sessions
   (FR-009) and serve as the Celery task broker for background ingestion jobs.
4. **Blob storage** — store raw policy document files (PDF, DOCX) uploaded via
   the admin console (FR-001, FR-031).

Enterprise standards mandate Azure PaaS-first for all data services.

---

## Decision

> We will use **Azure AI Search** for vector/hybrid search, **Azure Database
> for PostgreSQL Flexible Server** for relational data, **Azure Cache for
> Redis** for session state and Celery brokering, and **Azure Blob Storage**
> for raw document files.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Vector store | Azure PaaS-first | Azure AI Search | ✅ |
| Relational DB | Azure PaaS-first | Azure Database for PostgreSQL Flexible Server | ✅ |
| Cache/broker | Azure PaaS-first | Azure Cache for Redis | ✅ |
| Blob storage | Azure PaaS-first | Azure Blob Storage | ✅ |
| Encryption at rest | AES-256 (NFR-012) | All services support AES-256 | ✅ |
| TLS | 1.2+ (NFR-011) | All services enforce TLS 1.2+ | ✅ |

Reference: `governance/enterprise-standards.md`

---

## Options Considered

### Vector Store

#### Option A: Azure AI Search ← Chosen

**Description:** Use Azure AI Search (formerly Azure Cognitive Search) with
vector search capabilities for storing and querying document chunk embeddings.

**Pros:**
- Azure-native PaaS — fully managed, no infrastructure to operate
- Supports hybrid search: vector similarity + BM25 keyword search in a single
  query — directly enables the LLM fallback mode (NFR-006)
- Built-in semantic ranker for re-ranking search results
- Integrated with Azure OpenAI for embeddings generation
- Supports filtering by metadata fields (category, effective date, etc.)
- Scales to millions of documents (NFR-014 target of 500 docs is well within limits)
- Built-in support for document skillsets (PDF/DOCX cracking, chunking)

**Cons:**
- Cost is higher than self-managed vector databases at very large scale (not
  relevant at 500 documents)
- Less customizable than self-managed solutions

#### Option B: Azure Cosmos DB for MongoDB vCore (vector search)

**Pros:**
- Azure PaaS, supports vector search
- Combines document store with vector capabilities

**Cons:**
- Vector search is less mature than Azure AI Search
- No built-in hybrid search (BM25 + vector) in a single query
- Higher cost for the vector search tier
- No built-in document cracking skillsets

#### Option C: Self-managed Qdrant / Pinecone / Weaviate on AKS

**Pros:**
- Purpose-built vector databases with rich query capabilities

**Cons:**
- **Violates PaaS-first policy** — requires self-managed infrastructure on AKS
- Operational overhead for cluster management, backups, scaling
- Additional exception ADR required

---

### Relational Database

#### Option A: Azure Database for PostgreSQL Flexible Server ← Chosen

**Description:** Managed PostgreSQL for all relational data.

**Pros:**
- Enterprise-approved Azure PaaS service
- Consistent with expense-portal project (ADR-0002)
- Supports JSONB for semi-structured data (conversation logs, feedback)
- Point-in-time restore and automated backups
- AES-256 encryption at rest (NFR-012)
- Mature migration tooling (Alembic)

**Cons:**
- None significant for this workload

#### Option B: Azure Cosmos DB (NoSQL)

**Pros:**
- Multi-region distribution, low-latency reads

**Cons:**
- Overkill for this workload — no multi-region requirement
- Higher cost for the query patterns involved (relational joins for analytics)
- Less natural fit for analytics aggregation queries (FR-029)

---

### Session Store / Celery Broker

**Azure Cache for Redis** is the only governance-compliant option for both
caching and Celery brokering. It is the approved PaaS service for this purpose.

---

### Blob Storage

**Azure Blob Storage** is the standard Azure service for storing raw files.
No alternatives were considered.

---

## Consequences

### Positive
- All four storage services are Azure PaaS — zero self-managed infrastructure
- Azure AI Search's hybrid search enables both RAG and LLM-fallback keyword search
  from a single index
- PostgreSQL consistency with expense-portal reduces learning curve
- Azure Cache for Redis serves dual purpose (session cache + Celery broker),
  minimizing service count

### Negative / Trade-offs
- Four distinct storage services add deployment complexity (mitigated: all
  defined in Bicep, standard ACA-to-PaaS networking)
- Azure AI Search has a minimum SKU cost even at low query volumes

### Risks
- Azure AI Search query latency under heavy concurrent load — mitigated by
  selecting appropriate SKU (Standard S1 or S2) and load testing during UAT
- PostgreSQL connection pool exhaustion under 600 concurrent conversations —
  mitigated by connection pooling (PgBouncer built into Flexible Server)

---

## Implementation Notes

- **Azure AI Search:** Standard S1 SKU initially; index per policy corpus version;
  use the `azure-search-documents` Python SDK
- **PostgreSQL:** General Purpose tier, 4 vCores, 128 GB storage; use SQLAlchemy
  + Alembic for ORM and migrations
- **Azure Cache for Redis:** Standard C1; used as Celery broker
  (`redis://` connection string from Key Vault) and for conversation session state
  (FR-009, 90-day TTL per NFR-008)
- **Azure Blob Storage:** Standard LRS; container `policy-documents` for raw files
- All connection strings stored in Azure Key Vault — no secrets in code or config
- Data retention: conversation logs auto-purged after 90 days (NFR-008) via
  PostgreSQL scheduled job

---

## References
- `governance/enterprise-standards.md` — Cloud Service Preference Policy
- `docs/adr/ADR-0002-data-storage.md` — expense-portal PostgreSQL precedent
- Related: ADR-0007 (language), ADR-0010 (RAG architecture)
- Related requirements: FR-001, FR-003, FR-004, FR-006, FR-009, FR-012, FR-028,
  FR-029, FR-030, FR-031, FR-033, NFR-006, NFR-008, NFR-011, NFR-012, NFR-014
