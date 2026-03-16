# ADR-0007: Language Selection — Policy Chatbot

> **Status:** Proposed
> **Date:** 2026-03-16
> **Deciders:** Platform Engineering, HR Service Desk Manager
> **Project:** policy-chatbot

---

## Context

The Policy Chatbot requires a backend language for the API server, document
ingestion pipeline, RAG orchestration, and admin console. The system integrates
heavily with Azure OpenAI Service, Azure AI Search, and Microsoft Graph API.

The informal stakeholder request suggested Node.js as a potential option. The
requirements agent flagged this as a governance conflict (GOV-001).

Related requirements: FR-001–FR-033, NFR-001, NFR-009, NFR-013.

---

## Decision

> We will use **Python 3.11+** for all backend services in the Policy Chatbot
> because it is the approved language for AI/ML workloads, has first-class Azure
> SDK support, and the team has existing Python expertise from the expense-portal
> project.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Language | Python or Go only | Python 3.11+ | ✅ |
| Framework | FastAPI for REST APIs | FastAPI | ✅ |
| Background tasks | Celery + Redis | Celery + Azure Cache for Redis | ✅ |
| Package management | uv (preferred), pip | uv | ✅ |
| Code quality | ruff, mypy strict, pytest 80% coverage | All configured | ✅ |

Reference: `governance/enterprise-standards.md`

---

## Options Considered

### Option 1: Python 3.11+ ← Chosen

**Description:** Use Python with FastAPI for the API server and admin console,
Celery for background document ingestion jobs, and the Azure OpenAI Python SDK
for LLM integration.

**Pros:**
- Best-in-class ecosystem for AI/ML workloads: LangChain, Azure OpenAI SDK,
  Azure AI Search SDK, document parsing libraries (PyMuPDF, python-docx, BeautifulSoup)
- First-class Azure SDK support (`azure-ai-openai`, `azure-search-documents`,
  `azure-identity`, `azure-monitor-opentelemetry`)
- FastAPI provides async support for handling concurrent chat conversations (FR-010)
- Team has existing Python/FastAPI experience from expense-portal project
- Governance-compliant with no exception required
- Rich ecosystem for text processing, chunking, and embedding generation

**Cons:**
- Lower raw throughput than Go for CPU-bound workloads (mitigated: this system
  is I/O-bound, waiting on Azure OpenAI and Azure AI Search APIs)

---

### Option 2: Go 1.22+

**Description:** Use Go with chi router for the API server and native
goroutines for concurrent document processing.

**Pros:**
- Higher raw throughput and lower memory footprint
- Governance-compliant

**Cons:**
- Significantly weaker AI/ML ecosystem — no mature equivalent to LangChain,
  limited document parsing libraries for PDF/DOCX
- Azure OpenAI Go SDK is less mature than the Python SDK
- Team has less Go experience for this type of workload
- More boilerplate code for RAG pipeline orchestration

---

### Option 3: Node.js / TypeScript

**Description:** Use Node.js with a chatbot framework.

**Pros:**
- Good chatbot framework ecosystem (Bot Framework SDK)

**Cons:**
- **BLOCKED by enterprise language policy** — Node.js/TypeScript is explicitly
  prohibited for new projects
- Would require VP Engineering approval and an exception ADR
- No business justification exists when Python meets all requirements

---

## Consequences

### Positive
- Full access to Python AI/ML ecosystem accelerates RAG development
- Consistent technology stack with expense-portal project
- No governance exception process required

### Negative / Trade-offs
- Python is slower than Go for CPU-heavy operations (acceptable for this I/O-bound workload)
- GIL limits true CPU parallelism (mitigated by async I/O and Celery workers for background tasks)

### Risks
- Azure OpenAI SDK breaking changes during development — mitigated by pinning versions in `pyproject.toml`

---

## Implementation Notes

- Use `fastapi` for the API server (chat API, admin console API, health endpoints)
- Use `celery` with Azure Cache for Redis as broker for document ingestion background jobs
- Use `azure-ai-openai` SDK for LLM interactions
- Use `azure-search-documents` SDK for vector search operations
- Use `azure-identity` for Microsoft Entra ID authentication
- Use `azure-monitor-opentelemetry` for observability
- Python version: 3.11+ (per enterprise standards)
- Package manager: `uv`

---

## References
- `governance/enterprise-standards.md` — Language Policy, Framework Policy
- Requirements GOV-001 flag: Node.js blocked
- Related: ADR-0008 (compute platform), ADR-0010 (RAG architecture)
- Related requirements: FR-001–FR-033
