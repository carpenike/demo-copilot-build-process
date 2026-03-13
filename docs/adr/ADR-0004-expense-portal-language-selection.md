# ADR-0004: Language & Framework Selection for Expense Portal

> **Status:** Proposed
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering, Finance Systems Team
> **Project:** expense-portal (FIN-EXP-2026)

---

## Context

The Employee Expense Management Portal requires a backend service that exposes a REST API for expense submission, approval workflows, policy enforcement, reporting, and integrations with Workday and SAP S/4HANA. The frontend will be a mobile-responsive web application.

Key technical characteristics of this project:
- CRUD-heavy REST API with moderate business logic (policy engine, approval workflow)
- File upload handling (receipt images up to 10 MB)
- Integration with external systems via scheduled jobs (Workday nightly sync) and batch processing (SAP IDoc generation)
- OCR integration (Azure AI Document Intelligence API calls)
- ~2,400 users, peak 1,500 concurrent — moderate scale, not high-throughput
- Reporting dashboards with filtered queries and CSV export
- 7-year audit log retention (SOX compliance)

Related requirements: FR-001 through FR-024, NFR-001 through NFR-024.

---

## Decision

> We will use **Python 3.11+ with FastAPI** for the backend API service because it is the best fit for a CRUD-heavy REST API with integration-focused workloads, and it is the approved framework for REST APIs per enterprise standards.

> The frontend will be served as a **mobile-responsive web application** using server-rendered templates (Jinja2) with lightweight JavaScript for interactivity, avoiding the need for a separate frontend framework (which would require a prohibited language — TypeScript/Node.js).

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Language | Python or Go only | Python 3.11+ | ✅ |
| Framework | FastAPI for REST APIs | FastAPI | ✅ |
| Infrastructure | Docker, AKS, Terraform | OCI container on AKS | ✅ |
| Package management | uv (preferred), pip | uv | ✅ |
| Testing | pytest | pytest | ✅ |

---

## Options Considered

### Option 1: Python 3.11+ / FastAPI ← Chosen

**Description:** Python backend using FastAPI for the REST API layer. FastAPI provides automatic OpenAPI 3.1 schema generation, built-in request validation via Pydantic, and async support. Server-rendered Jinja2 templates for the web frontend.

**Pros:**
- FastAPI auto-generates OpenAPI 3.1 spec (NFR-020) with minimal effort
- Pydantic models provide request/response validation that maps directly to the data model
- Rich ecosystem for integrations: SAP RFC libraries, Workday API clients, Azure SDK
- Celery (approved for background tasks) integrates seamlessly for async jobs
- Jinja2 templating avoids introducing a prohibited frontend language/framework
- Team familiarity across Platform Engineering (per enterprise standard adoption)
- Fast development velocity — aligns with July 1 go-live target

**Cons:**
- Lower raw throughput than Go under extreme concurrency (not a concern at 1,500 peak users)
- Server-rendered frontend is less interactive than a SPA (acceptable for v1 — forms and dashboards)

---

### Option 2: Go 1.22+ / chi router

**Description:** Go backend using chi router for HTTP, with server-rendered templates (html/template).

**Pros:**
- Higher throughput and lower memory footprint per instance
- Strong concurrency model for parallel integration calls

**Cons:**
- Go's ecosystem for SAP IDoc generation and Workday API integration is less mature
- No equivalent to FastAPI's automatic OpenAPI schema generation — requires manual spec maintenance
- Slower development velocity for CRUD-heavy applications with complex validation logic
- html/template is more verbose than Jinja2 for form-heavy UIs
- The performance advantage is unnecessary at the expected scale (1,500 concurrent users)

---

### Option 3: Python API + TypeScript SPA (React/Next.js)

**Description:** FastAPI backend with a separate React or Next.js frontend.

**Pros:**
- Richer interactive UI experience
- Better separation of frontend and backend concerns

**Cons:**
- **TypeScript/Node.js is a prohibited language** per enterprise standards — would require VP Engineering exception
- Doubles the number of deployable artifacts and CI pipelines
- Adds complexity disproportionate to the UI requirements (forms + dashboards)

---

## Consequences

### Positive
- Single deployable service simplifies infrastructure, CI/CD, and operations
- OpenAPI spec generated automatically from code, always in sync
- Large Python ecosystem accelerates integration development
- Consistent with enterprise standard choices — no exceptions needed

### Negative / Trade-offs
- Server-rendered UI is less interactive than a SPA; acceptable for v1 (forms, tables, dashboards)
- Python's GIL limits CPU-bound parallelism; mitigated by offloading heavy work to Celery workers

### Risks
- If future requirements demand a highly interactive UI (drag-and-drop, real-time collaboration), a frontend framework exception may be needed. **Mitigation:** The API is cleanly separated behind versioned REST endpoints, so a future SPA frontend can be added without backend changes.

---

## Implementation Notes

- Use `uv` for package management
- FastAPI app structure: routers per domain (expenses, approvals, admin, reports, integrations)
- Pydantic v2 models for request/response schemas
- Jinja2 templates served via FastAPI's `Jinja2Templates` with HTMX for partial page updates (no prohibited language — HTMX is a JS library loaded via CDN, not a Node.js framework)
- `uvicorn` as the ASGI server inside the Docker container

---

## References
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Enterprise standards](../../governance/enterprise-standards.md)
- Related requirements: FR-001–FR-024, NFR-020, NFR-021
