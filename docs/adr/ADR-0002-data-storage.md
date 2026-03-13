# ADR-0002: Data Storage

> **Status:** Accepted
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering
> **Project:** example-ticket-app

---

## Context

The system requires persistent storage for tickets, comments, internal notes,
user data, and attachments. The stakeholder specified an existing PostgreSQL
database. Full-text search across ticket content is a key requirement (FR-010)
with a 500ms target on indices up to 1M tickets (NFR-002).

We need to decide: use PostgreSQL's built-in full-text search, or introduce a
dedicated search engine (e.g., Elasticsearch/OpenSearch)?

---

## Decision

> We will use **PostgreSQL** for primary data storage and **PostgreSQL full-text
> search** (tsvector + GIN index) for ticket search, avoiding a separate search
> engine for v1.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Infrastructure | Terraform + internal modules | RDS PostgreSQL via Terraform | ✅ |
| Secrets | AWS Secrets Manager | DB credentials via Secrets Manager | ✅ |

---

## Options Considered

### Option 1: PostgreSQL + built-in FTS ← Chosen

**Pros:**
- No additional infrastructure component — lower operational cost
- PostgreSQL FTS handles 1M documents comfortably with GIN indices
- Existing PostgreSQL expertise on the team
- Single source of truth — no sync lag between DB and search index

**Cons:**
- Less sophisticated ranking than Elasticsearch
- If search requirements grow significantly (faceted search, fuzzy matching), may need migration

---

### Option 2: PostgreSQL + OpenSearch

**Pros:**
- Superior search capabilities (faceted, fuzzy, autocomplete)
- Proven at massive scale

**Cons:**
- Additional infrastructure component to deploy, monitor, and maintain
- Data synchronization complexity (DB → search index)
- Overkill for the current scale and requirements

---

## Consequences

### Positive
- Simpler architecture — one data store
- Lower infrastructure cost
- No data sync issues

### Negative / Trade-offs
- FTS capabilities are more limited than a dedicated search engine
- If the search UX demands grow, this ADR may need to be superseded

### Risks
- **Risk:** Search performance degrades beyond 1M tickets
  - **Mitigation:** Monitor query latency; plan migration to OpenSearch as ADR-0002-v2 if needed

---

## Implementation Notes

- Add a `search_vector` tsvector column to the tickets table
- Create a GIN index on the search vector
- Use a PostgreSQL trigger to update the search vector on INSERT/UPDATE
- Fields included in search: subject, description, comment text

---

## References
- FR-010 (full-text search), NFR-002 (search latency target)
- Related: ADR-0001 (language selection)
