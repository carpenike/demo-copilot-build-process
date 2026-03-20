# ADR-0009: Policy Chatbot — Data Storage

> **Status:** Accepted
> **Date:** 2026-03-20
> **Deciders:** Platform Engineering, HR Service Desk Manager
> **Project:** policy-chatbot

---

## Context

The Policy Chatbot must persist several categories of data:

1. **Structured application data** — conversations, feedback, user profiles,
   document metadata, analytics aggregates (FR-004, FR-006, FR-028, FR-029)
2. **Session state** — active conversation context for follow-up resolution
   (FR-009, supporting 200+ concurrent sessions)
3. **Document corpus** — raw policy documents (PDF, DOCX, HTML) before and after
   text extraction (FR-001, FR-002)

Enterprise standards mandate Azure PaaS-first data services
(`governance/enterprise-standards.md` § Cloud Service Preference Policy).

---

## Decision

> We will use **Azure Database for PostgreSQL Flexible Server** for structured
> application data, **Azure Cache for Redis** for session state, and
> **Azure Blob Storage** for raw document files because these are the
> enterprise-approved Azure PaaS services that best fit each data category.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Relational DB | Azure PaaS preferred | Azure Database for PostgreSQL Flexible Server | ✅ |
| Cache | Azure PaaS preferred | Azure Cache for Redis | ✅ |
| Object storage | Azure PaaS preferred | Azure Blob Storage | ✅ |
| Encryption at rest | AES-256 (NFR-012) | PostgreSQL: enabled by default; Redis: encrypted; Blob: SSE | ✅ |
| Secrets | Azure Key Vault | Connection via Managed Identity (passwordless) | ✅ |

---

## Options Considered

### Option 1: PostgreSQL + Redis + Blob Storage ← Chosen

**Description:** Azure Database for PostgreSQL Flexible Server for relational
data, Azure Cache for Redis for session/conversation state, Azure Blob Storage
for raw document files.

**Pros:**
- PostgreSQL handles relational queries, JSON columns, full-text search — ideal
  for document metadata, feedback, analytics, and user data
- Redis provides sub-millisecond session lookups for conversation context — critical
  for the 5-second response SLA (NFR-001)
- Blob Storage is purpose-built for large binary files (PDF/DOCX) with tiering
  and lifecycle management
- All three support Managed Identity authentication (passwordless)
- All three are enterprise-approved Azure PaaS services
- PostgreSQL alembic migrations for schema versioning

**Cons:**
- Three separate data services to provision and monitor
- Redis adds a cost component for session state (justified by performance needs)

---

### Option 2: PostgreSQL + Blob Storage (no Redis)

**Description:** Store conversation session state in PostgreSQL instead of Redis.

**Pros:**
- One fewer service to manage
- Lower cost — no Redis tier

**Cons:**
- PostgreSQL round-trip for every message in a conversation adds ~5–15ms per
  query vs. <1ms for Redis — at scale this erodes the 5-second SLA budget
- Conversation sessions are ephemeral and high-throughput — a cache is the
  natural fit, not a relational database
- Under 200+ concurrent conversations, PostgreSQL session queries compete with
  analytics and metadata queries for connection pool capacity

---

### Option 3: Azure Cosmos DB (NoSQL) + Blob Storage

**Description:** Use Cosmos DB for both application data and session state.

**Pros:**
- Single database service for all non-blob data
- Global distribution if needed in the future
- Built-in TTL for session expiration

**Cons:**
- Higher cost per GB and per RU compared to PostgreSQL for relational queries
- Cosmos DB's NoSQL model is a poor fit for the relational queries needed by
  the analytics dashboard (FR-029) — joins, aggregations, time-series grouping
- Team has strong PostgreSQL experience; Cosmos DB would require learning a
  new data modeling paradigm
- Not the enterprise-preferred relational database

---

## Consequences

### Positive
- PostgreSQL's relational model supports the complex analytics queries
  (daily/weekly/monthly volumes, top intents, resolution rates) without
  additional tooling
- Redis ensures conversation context lookups do not impact the 5-second SLA
- Blob Storage provides cost-effective, durable storage for the document corpus
  with built-in versioning for FR-006

### Negative / Trade-offs
- Three services to provision, monitor, and back up
- Redis data is ephemeral by default — must configure persistence if session
  durability across restarts is needed (NFR-005)

### Risks
- PostgreSQL connection pool exhaustion under peak load — mitigated by
  connection pooling (PgBouncer built into Flexible Server) and connection
  limits in FastAPI's async pool
- Redis memory pressure — mitigated by TTL on session keys (30-minute
  inactivity timeout) and monitoring alerts

---

## Implementation Notes

### PostgreSQL
- **SKU:** General Purpose, 2 vCores (scale up based on load testing)
- **Version:** PostgreSQL 16
- **Auth:** Microsoft Entra ID authentication (Managed Identity)
- **Schema management:** Alembic migrations in `src/alembic/`
- **Key tables:** `documents`, `document_versions`, `conversations`, `messages`,
  `feedback`, `users`, `analytics_daily`

### Redis
- **SKU:** Basic C1 (upgrade to Standard for replication if needed)
- **Auth:** Microsoft Entra ID authentication
- **Key patterns:** `session:{conversation_id}` → JSON conversation context
- **TTL:** 30 minutes on session keys (configurable)

### Blob Storage
- **Container:** `policy-documents` for raw files, `extracted-text` for
  processed output
- **Auth:** Managed Identity with Storage Blob Data Contributor role
- **Versioning:** Blob versioning enabled for document version history (FR-006)
- **Lifecycle:** Move to Cool tier after 90 days for retired documents

---

## References
- [Azure Database for PostgreSQL Flexible Server](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/)
- [Azure Cache for Redis](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/)
- [Azure Blob Storage](https://learn.microsoft.com/en-us/azure/storage/blobs/)
- Related requirements: FR-001, FR-004, FR-006, FR-009, FR-028, FR-029, NFR-001, NFR-012
- Related ADRs: ADR-0010 (RAG architecture), ADR-0011 (document ingestion)
