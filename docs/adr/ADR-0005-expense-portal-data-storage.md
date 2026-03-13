# ADR-0005: Data Storage for Expense Portal

> **Status:** Proposed
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering, Finance Systems Team
> **Project:** expense-portal (FIN-EXP-2026)

---

## Context

The Expense Portal requires persistent storage for:
1. **Relational data** — expense reports, line items, approval workflow state, policy rules, audit logs, user/role mappings synced from Workday
2. **File/blob storage** — receipt images (JPEG, PNG, PDF up to 10 MB each) with 7-year retention for IRS compliance (NFR-014)
3. **Audit logs** — immutable approval action records retained for 7 years (NFR-011, NFR-015)

Key constraints:
- AES-256 encryption at rest (NFR-009)
- SOX compliance: immutable audit trail, no post-approval edits (NFR-015)
- Cursor-based pagination on list endpoints (NFR-022)
- ~2,400 users, moderate write volume (expense reports), high read volume on dashboards
- Must run on AKS / Azure infrastructure (enterprise standard)

Related requirements: FR-001–FR-021, NFR-006, NFR-009, NFR-011, NFR-013–NFR-015.

---

## Decision

> We will use **Azure Database for PostgreSQL — Flexible Server** for relational data and **Azure Blob Storage** for receipt images because they provide the required durability, encryption, compliance capabilities, and are native Azure services aligned with our AKS infrastructure.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Infrastructure | Azure / AKS ecosystem | Azure PG Flexible Server + Azure Blob Storage | ✅ |
| Secrets | Azure Key Vault | DB connection string stored in Key Vault | ✅ |
| Encryption at rest | AES-256 | Azure PG: TDE with platform-managed keys; Blob: SSE with AES-256 | ✅ |
| TLS | 1.2+ | Azure PG enforces TLS 1.2; Blob Storage enforces TLS 1.2 | ✅ |

---

## Options Considered

### Option 1: Azure PostgreSQL + Azure Blob Storage ← Chosen

**Description:** Azure Database for PostgreSQL — Flexible Server for all relational data (reports, line items, approvals, policy config, audit logs). Azure Blob Storage with immutable blob policies for receipt file storage.

**Pros:**
- PostgreSQL is mature, well-supported by SQLAlchemy/asyncpg in the Python ecosystem
- Native cursor-based pagination support via keyset pagination
- Azure PG Flexible Server provides automated backups, point-in-time restore, and HA within AKS region
- Azure Blob Storage immutability policies satisfy SOX/IRS 7-year retention requirements
- Both services provide AES-256 encryption at rest by default
- Both are Azure-native — simplified networking (private endpoints within AKS VNet)

**Cons:**
- PostgreSQL requires schema migration management (mitigated by Alembic)
- Blob Storage adds a second storage dependency (but receipt files don't belong in a relational DB)

---

### Option 2: Azure Cosmos DB (NoSQL)

**Description:** Use Cosmos DB for all data including expense reports, approvals, and audit logs.

**Pros:**
- Auto-scaling, globally distributed (not needed — single region is sufficient)
- Flexible schema

**Cons:**
- Complex relational queries (joins for dashboard reporting by cost center, category, period) are awkward and expensive in a document model
- No native support for the relational integrity needed for approval workflows (foreign keys, constraints)
- Higher cost for the moderate-scale, join-heavy query patterns of this application
- Over-engineered for single-region, ~2,400-user workload

---

### Option 3: Azure SQL Database

**Description:** Microsoft SQL Server managed service.

**Pros:**
- Mature relational database with excellent Azure integration
- Good reporting query performance

**Cons:**
- No strong technical reason to prefer over PostgreSQL for this workload
- PostgreSQL has better Python ecosystem support (asyncpg, SQLAlchemy async drivers)
- Enterprise standards don't restrict database choice, but team has more PostgreSQL experience

---

## Consequences

### Positive
- Clean separation: relational data in PostgreSQL, files in Blob Storage — each optimized for its workload
- Immutable blob policies provide built-in compliance for receipt retention
- Point-in-time restore and automated backups reduce operational risk
- Private endpoints keep all data traffic within the AKS VNet

### Negative / Trade-offs
- Two storage services to manage (PostgreSQL + Blob) adds operational surface area
- Schema migrations (Alembic) require careful CI/CD integration

### Risks
- Database connection pool exhaustion under peak load. **Mitigation:** Use asyncpg connection pooling with pool size tuned to 1,500 concurrent user target; monitor via `/metrics` endpoint.
- Blob Storage cost for 7-year receipt retention. **Mitigation:** Use Cool storage tier for receipts older than 90 days; lifecycle management policy to auto-tier.

---

## Implementation Notes

- **ORM:** SQLAlchemy 2.0 with async support (asyncpg driver)
- **Migrations:** Alembic for schema versioning, migrations committed to repo
- **Connection string:** Stored in Azure Key Vault, injected via CSI secrets driver in AKS
- **Blob access:** Azure SDK for Python (`azure-storage-blob`), SAS tokens for time-limited receipt download URLs served to the frontend
- **Audit log table:** Append-only table with database-level constraints (no UPDATE/DELETE triggers); `created_at` timestamp, actor ID, action, IP address, report ID
- **Immutable receipts:** Azure Blob immutability policy (WORM) with 7-year retention; legal hold capability for audit investigations
- **Soft deletes:** Expense reports use soft delete (status = "cancelled") — never hard delete, per SOX

---

## References
- [Azure Database for PostgreSQL — Flexible Server](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/)
- [Azure Blob Storage immutability policies](https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview)
- Related ADRs: ADR-0004 (language selection)
- Related requirements: FR-001–FR-021, NFR-006, NFR-009, NFR-011, NFR-013–NFR-015
