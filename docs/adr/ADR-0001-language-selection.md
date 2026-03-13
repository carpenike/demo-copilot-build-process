# ADR-0001: Backend Language Selection

> **Status:** Accepted
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering, Support Operations
> **Project:** example-ticket-app

---

## Context

The stakeholder request specified Node.js for the backend because "our frontend
team knows it." However, Node.js is a **prohibited language** under the enterprise
language policy (see `governance/enterprise-standards.md`). Only Python and Go are
approved for new backend services.

The system requires a REST API with moderate throughput (~100 req/s), database
integration (PostgreSQL), background email dispatch, and full-text search. Both
Python and Go are capable of meeting these requirements.

Related requirements: FR-001 through FR-016, NFR-001 (200ms p95 latency).

---

## Decision

> We will use **Python 3.11+ with FastAPI** for the backend API because it provides
> the fastest development velocity for a CRUD-heavy REST API with standard
> integrations, and it is the approved framework for REST APIs.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Language | Python or Go only | Python 3.11+ | ✅ |
| Framework | FastAPI (REST APIs) | FastAPI | ✅ |
| Infrastructure | Docker + EKS | Docker + EKS | ✅ |

---

## Options Considered

### Option 1: Python + FastAPI ← Chosen

**Description:** Python 3.11+ with FastAPI for the REST API, async throughout,
Pydantic for request/response validation.

**Pros:**
- Approved language and framework — zero governance friction
- Excellent async support for I/O-bound workload (DB, email, search)
- Pydantic provides automatic OpenAPI spec generation
- Rich ecosystem for all required integrations (SQLAlchemy, SendGrid SDK, etc.)
- Team velocity: fastest path to a working API

**Cons:**
- Single-threaded per worker (mitigated by async + multiple workers)
- Higher memory footprint than Go for equivalent throughput

---

### Option 2: Go + chi router

**Description:** Go 1.22+ with chi router for HTTP, standard library for the rest.

**Pros:**
- Approved language and framework
- Lower memory/CPU per request
- Excellent for high-throughput scenarios

**Cons:**
- Higher development time for a CRUD-heavy API (more boilerplate)
- Weaker ORM ecosystem compared to Python/SQLAlchemy
- Throughput ceiling not relevant for this workload (~100 req/s vs Go's capacity)

---

### Option 3: Node.js + Express ← Rejected (governance)

**Description:** The stakeholder's original suggestion.

**Pros:**
- Frontend team familiarity

**Cons:**
- **PROHIBITED** by enterprise language policy — disqualified

---

## Consequences

### Positive
- Full governance compliance from day one
- Automatic OpenAPI spec generation via FastAPI
- Strong typing via Pydantic reduces runtime errors

### Negative / Trade-offs
- Frontend team may need onboarding on Python (mitigated by code style standards)
- Slightly higher memory per container vs Go

### Risks
- None significant — Python + FastAPI is the most well-trodden path for this use case

---

## Implementation Notes

- Use `uvicorn` as the ASGI server with multiple workers
- Use `pydantic-settings` for configuration management
- Use `sqlalchemy[asyncio]` with `asyncpg` driver for async database access
- Package management via `uv` (preferred per enterprise standards)

---

## References
- [Governance conflict: LANG-001 in requirements.md](../../projects/example-ticket-app/requirements/requirements.md)
- Related: ADR-0002 (data storage), ADR-0003 (email integration)
