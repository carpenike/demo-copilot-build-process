# ADR-0010: Policy Chatbot — RAG Architecture & LLM Integration

> **Status:** Proposed
> **Date:** 2026-03-17
> **Deciders:** Platform Engineering
> **Project:** policy-chatbot

---

## Context

The core value proposition of the policy chatbot is answering employee questions
with policy-grounded, cited, and actionable responses. This requires a
retrieval-augmented generation (RAG) architecture that:

1. Ingests and chunks policy documents (FR-001–FR-003)
2. Generates vector embeddings for semantic retrieval (FR-003)
3. Retrieves relevant document chunks given a user query (FR-012)
4. Generates a natural language answer grounded in retrieved content (FR-012–FR-014)
5. Produces citations linking every claim to a source document (FR-013)
6. Detects procedural queries and generates checklists (FR-017–FR-021)
7. Detects confidential/sensitive topics and blocks AI-generated answers (FR-016)

The enterprise standard mandates **Azure OpenAI Service** as the LLM provider
(NFR-009). The data storage ADR (ADR-0009) establishes **Azure AI Search** as the
vector store. This ADR defines how these components integrate into a RAG pipeline.

---

## Decision

> We will implement a **hybrid RAG pipeline** using **Azure OpenAI Service** for
> embeddings and completions, and **Azure AI Search** for vector + keyword
> retrieval with semantic ranking. The pipeline enforces grounded generation
> with mandatory citation extraction and confidence scoring.

### Pipeline Overview

```
User Query
    │
    ├─ 1. Intent Classification (Azure OpenAI — GPT-4o)
    │      → Classify: domain, query type (factual/procedural/sensitive)
    │      → If sensitive → escalate immediately (FR-016)
    │
    ├─ 2. Query Enrichment
    │      → Expand query with conversation context (FR-009)
    │      → Generate search query variants
    │
    ├─ 3. Retrieval (Azure AI Search)
    │      → Hybrid search: vector similarity + BM25 keyword
    │      → Semantic re-ranking of top results
    │      → Return top-k chunks with metadata
    │
    ├─ 4. Answer Generation (Azure OpenAI — GPT-4o)
    │      → System prompt enforces grounded generation
    │      → Chunks injected as context
    │      → Output: answer + citations + confidence score
    │      → If procedural: generate checklist (FR-017)
    │
    └─ 5. Post-Processing
           → Validate citations exist in retrieved chunks
           → Append disclaimer (FR-015)
           → If confidence < threshold → auto-escalate (FR-027)
           → Return response to user
```

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| LLM provider | Azure OpenAI Service only | Azure OpenAI Service | ✅ |
| Data residency | Corporate Azure tenant | All data stays in tenant | ✅ |
| No external training | NFR-009 | Azure OpenAI does not train on customer data | ✅ |
| Observability | Azure Monitor + OpenTelemetry | OTel traces on every pipeline stage | ✅ |

---

## Options Considered

### RAG Orchestration

#### Option 1: Custom pipeline with Azure SDKs ← Chosen

**Description:** Build the RAG pipeline directly using `openai` (Azure-configured)
and `azure-search-documents` Python SDKs, with custom orchestration code in
FastAPI route handlers and service classes.

**Pros:**
- Full control over retrieval, prompt engineering, and post-processing
- No framework lock-in — uses standard Azure SDKs
- Easier to debug and trace (each step is explicit)
- Lighter dependency footprint
- Custom citation extraction and confidence scoring logic

**Cons:**
- More boilerplate than a framework-based approach
- Must implement conversation memory, prompt templates, and retry logic manually

#### Option 2: LangChain orchestration

**Description:** Use LangChain's retrieval chain abstractions with Azure
integrations.

**Pros:**
- Pre-built chain and retrieval abstractions
- Large community and example repository

**Cons:**
- Heavy abstraction layer that obscures debugging
- Frequent breaking changes across versions
- Adds a large dependency tree
- Custom citation and checklist logic still requires breaking out of LangChain
  abstractions, negating many benefits
- Harder to trace and instrument for Azure Monitor

#### Option 3: Semantic Kernel (Microsoft)

**Description:** Microsoft's Semantic Kernel SDK for orchestrating LLM calls.

**Pros:**
- Microsoft-first-party SDK
- Good Azure OpenAI integration
- Plugin architecture for extensibility

**Cons:**
- Python SDK is less mature than the .NET version
- Smaller community and fewer production references in Python
- Adds abstraction without clear benefit over direct SDK usage for this use case

### LLM Model Selection

#### Option A: GPT-4o ← Chosen for answer generation

**Description:** Azure OpenAI GPT-4o deployment for intent classification and
answer generation.

**Pros:**
- Best reasoning and instruction-following capabilities
- Strong at structured output (citations, checklists)
- Adequate speed for the 5-second p95 SLA (NFR-001)

**Cons:**
- Higher per-token cost than GPT-4o-mini

#### Option B: GPT-4o-mini for intent classification

**Description:** Use GPT-4o-mini for the initial intent classification step to
reduce cost, while keeping GPT-4o for answer generation.

**Pros:**
- Lower cost for the classification step
- Faster response for classification

**Decision:** Use GPT-4o-mini for intent classification and GPT-4o for answer
generation. This is a cost optimization, not a separate ADR decision.

### Embedding Model

> **text-embedding-3-large** (3072 dimensions) for document chunk embeddings.
> Superior retrieval accuracy justifies the slightly higher cost over
> text-embedding-ada-002.

---

## Consequences

### Positive
- Full control over the RAG pipeline — no framework lock-in
- Each pipeline stage is independently testable and traceable
- Azure-native throughout — consistent with enterprise standards
- Citation validation ensures FR-013/FR-014 compliance (no hallucinated sources)
- Confidence scoring enables automatic escalation (FR-027)

### Negative / Trade-offs
- More custom code than a framework-based approach
- Must implement and maintain conversation context management, prompt templates,
  and retry/fallback logic
- Two LLM deployments (GPT-4o + GPT-4o-mini) to manage quota for

### Risks
- Azure OpenAI rate limits under peak load (600 concurrent conversations) —
  mitigated by configuring adequate TPM quota and implementing request queuing
- Prompt injection attacks — mitigated by input sanitization and system prompt
  hardening (the system only answers from indexed policy content)
- LLM service outage — mitigated by NFR-006 keyword fallback (US-015)

---

## Implementation Notes

### Prompt Engineering
- System prompt must enforce: "Answer ONLY from the provided context. If the
  context does not contain the answer, say you don't know."
- Citation format: `[Source: {document_title}, Section: {section}, Effective:
  {date}]`
- Checklist format: structured JSON output parsed by the API layer
- Sensitive topic detection: system prompt includes a classifier preamble

### Conversation Context
- Store conversation history in Redis with session TTL (30 minutes)
- Include last N messages as context in the LLM prompt (sliding window)
- Reset context when topic change is detected

### Confidence Scoring
- Use LLM-generated confidence (0.0–1.0) plus retrieval score from AI Search
- If combined confidence < 0.6 for two consecutive answers → auto-escalate

### Fallback Mode (NFR-006)
- If Azure OpenAI is unreachable, bypass LLM and return top-k AI Search results
  as raw keyword matches with a "basic search" disclaimer

---

## References
- ADR-0009: Policy Chatbot — Data Storage (Azure AI Search, PostgreSQL)
- Governance: `governance/enterprise-standards.md` § Cloud Service Preference Policy
- Requirements: FR-003, FR-008, FR-009, FR-012–FR-017, FR-027, NFR-001, NFR-006, NFR-009
