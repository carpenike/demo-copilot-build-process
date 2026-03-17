# ADR-0007: Policy Chatbot — Language Selection

> **Status:** Proposed
> **Date:** 2026-03-17
> **Deciders:** Platform Engineering
> **Project:** policy-chatbot

---

## Context

The Corporate Policy Assistant Chatbot requires a language and framework selection
for its backend services. The system's core workload is retrieval-augmented
generation (RAG): ingesting policy documents, generating vector embeddings,
querying Azure AI Search, calling Azure OpenAI for answer generation, and serving
the results via a REST API.

The stakeholder request (`projects/policy-chatbot/input/request.md`) suggested
Node.js, which is prohibited by the enterprise language policy. The BRD
(`projects/policy-chatbot/input/business-requirements.md`) acknowledges the
constraint: "Only Python and Go are approved for new backend services."

Requirements coverage: FR-001–FR-033, NFR-001–NFR-018.

---

## Decision

> We will use **Python 3.11+ with FastAPI** for all policy-chatbot backend
> services because the workload is I/O-bound (LLM API calls, vector search,
> document parsing) and Python has the strongest ecosystem for AI/ML, document
> processing, and Azure OpenAI SDK integration.

This inherits the platform-wide decision in ADR-0001.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Language | Python or Go only | Python 3.11+ | ✅ |
| Framework | FastAPI for REST APIs | FastAPI | ✅ |
| Background tasks | Celery + Redis | Celery + Azure Cache for Redis | ✅ |
| Package management | uv (preferred) | uv | ✅ |
| Code quality | ruff + mypy strict | Configured per standards | ✅ |

---

## Options Considered

### Option 1: Python 3.11+ with FastAPI ← Chosen

**Description:** Python with FastAPI for the REST API layer, Celery for background
document indexing tasks, Azure SDK libraries for all Azure service integrations.

**Pros:**
- Best-in-class ecosystem for AI/ML workloads: `openai`, `azure-ai-formrecognizer`,
  `azure-search-documents`, `langchain` (if needed)
- FastAPI provides async request handling ideal for I/O-bound LLM API calls
- Pydantic models generate OpenAPI spec automatically
- Rich document parsing libraries (`pypdf`, `python-docx`, `beautifulsoup4`)
- Azure OpenAI Python SDK is the most mature and feature-complete
- Consistent with the expense-portal project (team familiarity)

**Cons:**
- Higher memory per worker than Go (mitigated by ACA horizontal scaling)
- GIL limits CPU-bound parallelism (not a concern — workload is I/O-bound)

### Option 2: Go 1.22+ with chi router

**Description:** Go for all backend services, using Azure SDK for Go.

**Pros:**
- Lower memory and CPU per request
- Strong concurrency model

**Cons:**
- Azure OpenAI SDK for Go is less mature than Python SDK
- Document parsing ecosystem is significantly weaker (no equivalent to pypdf,
  python-docx, beautifulsoup4 in Go)
- AI/ML tooling heavily favors Python — Go would require more custom code
- Longer development time for RAG pipeline implementation

### Option 3: Node.js ← Rejected (governance violation)

**Description:** Stakeholder-suggested option.

**Cons:**
- Prohibited by enterprise language policy
- Would require VP Engineering exception approval and ADR
- No business justification to override the policy given Python meets all needs

---

## Consequences

### Positive
- Fastest development velocity for RAG/AI workloads
- Mature Azure SDK integration
- Team familiar with Python from expense-portal project
- Rich document processing ecosystem eliminates need for external parsing services

### Negative / Trade-offs
- Slightly higher memory footprint than Go per worker instance
- Must tune worker count and ACA scaling to meet NFR-010 (200 concurrent conversations)

### Risks
- None significant — Python is the natural fit for this workload type

---

## Implementation Notes

- Use `uv` for package management
- FastAPI with `uvicorn` ASGI server
- Celery workers for document ingestion/indexing background tasks
- Azure SDK packages: `azure-identity`, `openai` (Azure-configured),
  `azure-search-documents`, `azure-storage-blob`
- OpenTelemetry with `azure-monitor-opentelemetry` for observability

---

## References
- ADR-0001: Platform Language and Framework Policy
- Governance: `governance/enterprise-standards.md` § Language Policy
- Requirements: FR-001–FR-033
