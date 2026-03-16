# ADR-0001: Platform Language and Framework Policy

> **Status:** Accepted
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering, VP Engineering
> **Scope:** All projects

---

## Context

New projects frequently arrive with stakeholder preferences for languages outside
the enterprise standard (e.g., Node.js, Java, Rust). Without a clear foundational
ADR, each project re-litigates the language decision. This ADR establishes the
platform-wide language and framework policy that all project-level ADRs inherit.

The enterprise language policy (`governance/enterprise-standards.md`) permits only
**Python** and **Go** for new backend services. This ADR documents the rationale
and provides guidance on when to choose each.

---

## Decision

> All new backend services MUST use either **Python 3.11+ with FastAPI** or
> **Go 1.22+ with chi router**, selected based on workload characteristics.
> Project-level ADRs reference this decision and justify their specific choice.

### Selection Guidance

| Workload Characteristic | Recommended Language |
|-------------------------|---------------------|
| CRUD-heavy REST APIs | Python + FastAPI |
| Data pipelines, ML/AI | Python |
| High-throughput services (>1000 req/s) | Go + chi |
| CLI tools, infrastructure tooling | Go + cobra |
| Background task processing | Python + Celery (or Go depending on service language) |

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Language | Python or Go only | Python 3.11+ | ✅ |
| Framework | FastAPI (REST APIs) | FastAPI | ✅ |
| Infrastructure | Docker + AKS | Docker + AKS | ✅ |

---

## Options Considered

### Option 1: Python + FastAPI ← Approved for CRUD/API workloads

**Description:** Python 3.11+ with FastAPI for REST APIs, async throughout,
Pydantic for request/response validation.

**Pros:**
- Approved language and framework — zero governance friction
- Excellent async support for I/O-bound workloads (DB, email, search)
- Pydantic provides automatic OpenAPI spec generation
- Rich ecosystem for integrations (SQLAlchemy, Azure SDKs, etc.)
- Fastest development velocity for CRUD-heavy APIs

**Cons:**
- Single-threaded per worker (mitigated by async + multiple workers)
- Higher memory footprint than Go for equivalent throughput

---

### Option 2: Go + chi router ← Approved for high-throughput workloads

**Description:** Go 1.22+ with chi router for HTTP, standard library for the rest.

**Pros:**
- Approved language and framework
- Lower memory/CPU per request
- Excellent for high-throughput and latency-sensitive scenarios
- Strong concurrency model

**Cons:**
- Higher development time for CRUD-heavy APIs (more boilerplate)
- Weaker ORM ecosystem compared to Python/SQLAlchemy

---

### Option 3: Node.js, Java, Rust, etc. ← Rejected (governance)

**Description:** Any language outside the approved list.

**Cons:**
- **PROHIBITED** by enterprise language policy — disqualified
- Requires VP Engineering exception approval and a dedicated ADR

When a stakeholder requests a prohibited language, the @1-requirements agent
flags it as a governance conflict. The @2-design agent then selects the best
approved alternative and documents the trade-off in the project-level ADR.

---

## Consequences

### Positive
- Full governance compliance from day one for all projects
- Automatic OpenAPI spec generation via FastAPI (Python path)
- Strong typing via Pydantic reduces runtime errors (Python path)
- Consistent tooling and CI/CD templates across all services

### Negative / Trade-offs
- Teams with non-Python/Go backgrounds may need onboarding
- Two languages means maintaining two CI templates and two sets of conventions

### Risks
- None significant — Python + FastAPI and Go + chi are well-proven stacks

---

## Implementation Notes

### Python projects
- Use `uvicorn` as the ASGI server with multiple workers
- Use `pydantic-settings` for configuration management
- Use `sqlalchemy[asyncio]` with `asyncpg` driver for async database access
- Package management via `uv` (preferred per enterprise standards)

### Go projects
- Use `chi` router for HTTP
- Use `context.Context` propagation for all I/O
- Use `gofmt` and `golint` with zero warnings

---

## References
- `governance/enterprise-standards.md` — Language Policy section
- Project-level ADRs that inherit this decision: ADR-0004 (expense-portal)
