# ADR-0002: Platform Data Storage Strategy

> **Status:** Accepted
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering
> **Scope:** All projects

---

## Context

Services in the platform require relational data storage. Rather than evaluating
database engines per-project, this ADR establishes **Azure Database for PostgreSQL
Flexible Server** as the standard relational data store. Projects that need
full-text search must decide between PostgreSQL’s built-in capabilities and a
dedicated search engine.

This ADR also establishes the principle: prefer PostgreSQL built-in features
(FTS, JSONB, partitioning) over introducing additional infrastructure components
unless scale or requirements demand it.

---

## Decision

> All services requiring relational storage MUST use **Azure Database for
> PostgreSQL Flexible Server**, provisioned via Terraform internal modules.
> Full-text search SHOULD use PostgreSQL built-in FTS (tsvector + GIN index)
> unless the project ADR justifies a dedicated search engine.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Infrastructure | Terraform + internal modules | Azure Database for PostgreSQL via Terraform | ✅ |
| Secrets | Azure Key Vault | DB credentials via Key Vault | ✅ |

---

## Options Considered

### Option 1: PostgreSQL + built-in FTS ← Default

**Pros:**
- No additional infrastructure component — lower operational cost
- PostgreSQL FTS handles millions of documents comfortably with GIN indices
- Single source of truth — no sync lag between DB and search index
- Consistent across all projects

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
- **Risk:** Search performance degrades at very high document counts
  - **Mitigation:** Monitor query latency per project; plan migration to OpenSearch as a superseding ADR if needed

---

## Implementation Notes

- Each service gets its own database on the shared Flexible Server instance
- For FTS: add a `search_vector` tsvector column with a GIN index
- Use a PostgreSQL trigger to update the search vector on INSERT/UPDATE
- DB credentials stored in Azure Key Vault, loaded via External Secrets Operator

---

## References
- `governance/enterprise-standards.md` — Infrastructure & Deployment Policy
- Related: ADR-0001 (language selection), ADR-0004 (authentication)
