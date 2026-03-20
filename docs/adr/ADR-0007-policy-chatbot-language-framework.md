# ADR-0007: Policy Chatbot — Language and Framework Selection

> **Status:** Accepted
> **Date:** 2026-03-20
> **Deciders:** Platform Engineering, HR Service Desk Manager
> **Project:** policy-chatbot

---

## Context

The Policy Chatbot requires a backend service that exposes REST APIs for
conversational interactions, document ingestion, admin operations, and analytics.
The service must integrate with Azure OpenAI, Azure AI Search, and Azure Blob
Storage, handle 200+ concurrent conversations (FR-010), and return responses
within 5 seconds (NFR-001).

The enterprise language policy permits only Python and Go for new projects
(`governance/enterprise-standards.md` § Language Policy).

---

## Decision

> We will use **Python 3.11+ with FastAPI** as the language and framework for
> the Policy Chatbot because it has the strongest Azure AI SDK ecosystem, the
> team has deep Python experience, and FastAPI's async support aligns with the
> high-concurrency, I/O-bound workload.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Language | Python or Go only | Python 3.11+ | ✅ |
| Framework | FastAPI (Python REST APIs) | FastAPI | ✅ |
| Package management | uv (preferred) | uv | ✅ |
| Testing | pytest | pytest | ✅ |
| Linting | ruff + mypy strict | ruff + mypy strict | ✅ |

---

## Options Considered

### Option 1: Python 3.11+ / FastAPI ← Chosen

**Description:** Python with FastAPI for the HTTP layer, using the official
Azure SDKs (`azure-ai-openai`, `azure-search-documents`, `azure-identity`,
`azure-storage-blob`).

**Pros:**
- First-class Azure AI SDK support — `openai` (Azure-backed), `azure-search-documents`,
  `azure-ai-formrecognizer` all have mature Python clients
- FastAPI's native async/await maps directly to the I/O-bound pattern of calling
  Azure OpenAI + AI Search per request
- Pydantic v2 for request/response validation — strong typing with minimal boilerplate
- Extensive NLP/AI ecosystem (LangChain, semantic-kernel, tiktoken) if needed
- Team has production experience with FastAPI from the Expense Portal project

**Cons:**
- Python is slower than Go for CPU-bound tasks (not a concern here — workload
  is I/O-bound)
- GIL limits true parallelism (mitigated by async I/O and uvicorn workers)

---

### Option 2: Go 1.22+ / chi router

**Description:** Go with the chi HTTP router, using the Azure SDK for Go.

**Pros:**
- Lower memory footprint per concurrent connection
- Goroutine-based concurrency is excellent for high fan-out patterns
- Strong compile-time type safety

**Cons:**
- Azure OpenAI SDK for Go is less mature than the Python SDK — fewer examples,
  less community support for RAG patterns
- No equivalent to LangChain or semantic-kernel in Go — would need to build
  prompt orchestration from scratch
- Team would need to develop new expertise; no prior Go production deployments
- Longer development timeline for AI integration code

---

### Option 3: Python 3.11+ / Django REST Framework

**Description:** Python with Django and DRF for the HTTP layer.

**Pros:**
- Django ORM simplifies database interactions
- Built-in admin interface could accelerate admin console development

**Cons:**
- Django's synchronous-first design is a poor fit for async Azure AI SDK calls
- Heavier framework with more boilerplate than FastAPI
- Not on the enterprise approved framework list (FastAPI is the approved choice)
- Slower startup and higher memory usage

---

## Consequences

### Positive
- Fastest path to production — leverages existing team skills and mature Azure SDKs
- Async FastAPI + uvicorn can handle 200+ concurrent conversations on modest ACA resources
- Pydantic models serve as both API contracts and documentation

### Negative / Trade-offs
- Python's memory usage per worker is higher than Go — mitigated by ACA auto-scaling
- Must be disciplined about async — blocking calls in endpoint handlers will
  degrade concurrency

### Risks
- Azure OpenAI SDK breaking changes — mitigated by pinning versions in `pyproject.toml`
- Performance under peak load — mitigated by load testing during UAT phase

---

## Implementation Notes

- Use `uv` for dependency management with `pyproject.toml`
- FastAPI app structure: `app/main.py` with routers in `app/api/`
- Use `azure-identity` `DefaultAzureCredential` for all Azure service auth
- Use `uvicorn` with `--workers` flag for multi-process concurrency
- Configure ruff with the mandatory rule set from enterprise standards
- Configure mypy in strict mode with pydantic plugin

---

## References
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Azure OpenAI Python SDK](https://learn.microsoft.com/en-us/azure/ai-services/openai/quickstart)
- Related requirements: FR-007, FR-010, NFR-001, NFR-013
- Related ADRs: ADR-0008 (compute platform), ADR-0010 (RAG architecture)
