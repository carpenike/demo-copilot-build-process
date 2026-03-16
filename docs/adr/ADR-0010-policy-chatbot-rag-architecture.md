# ADR-0010: RAG Architecture & LLM Service — Policy Chatbot

> **Status:** Proposed
> **Date:** 2026-03-16
> **Deciders:** Platform Engineering, HR Service Desk Manager
> **Project:** policy-chatbot

---

## Context

The Policy Chatbot's core capability is retrieval-augmented generation (RAG):
answering employee questions by retrieving relevant policy document chunks and
generating grounded, cited responses via an LLM. The system must:

- Produce answers grounded exclusively in indexed policy content (FR-012, FR-014)
- Include citations with document title, section, effective date, and source link (FR-013)
- Generate procedural checklists classified as Assisted or Manual (FR-017–FR-020)
- Detect confidential HR topics and suppress AI answers (FR-016)
- Maintain conversation context for follow-up questions (FR-009)
- Fall back to keyword search when the LLM is unavailable (NFR-006)
- Achieve ≥ 85% answer relevance and zero hallucinations (NFR-015, NFR-016)

Enterprise standards (NFR-009, BRD §7.2) mandate that all LLM interactions
use Azure OpenAI Service within the corporate Azure tenant. The requirements
agent flagged the stakeholder suggestion to use "ChatGPT's API directly" as
governance conflict GOV-002.

---

## Decision

> We will implement a **RAG pipeline using Azure OpenAI Service for LLM
> inference and Azure AI Search for vector retrieval**, following a
> retrieve-then-generate architecture with structured prompt templates for
> citation enforcement and checklist generation.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| LLM provider | Azure OpenAI Service only | Azure OpenAI Service | ✅ |
| Data residency | Corporate Azure tenant | Same-tenant deployment | ✅ |
| No external LLM training | NFR-009 | Data stays within Azure OpenAI | ✅ |
| Observability | Azure Monitor + OpenTelemetry | OTEL → Application Insights | ✅ |

Reference: `governance/enterprise-standards.md`, `governance/enterprise-standards.md` § Observability

---

## Options Considered

### Option 1: Azure OpenAI + Azure AI Search RAG ← Chosen

**Description:** Use Azure OpenAI Service (GPT-4o) for chat completion and
embedding generation, Azure AI Search for hybrid vector + keyword retrieval,
and structured prompt templates to enforce citation and grounding.

**Pros:**
- Fully Azure-native — Azure OpenAI and Azure AI Search are both PaaS
- Azure AI Search "On Your Data" feature provides a pre-built RAG pattern
  with grounding, citation, and content filtering
- Hybrid search (vector + BM25) in Azure AI Search directly enables the
  keyword fallback mode (NFR-006)
- Prompt engineering controls grounding: system prompts instruct the model
  to only answer from retrieved context and include citations
- Azure OpenAI content filtering provides an additional safety layer for
  detecting sensitive/confidential topics (FR-016)
- Embedding model (text-embedding-3-large) and chat model (GPT-4o) deployed
  in the same Azure OpenAI resource — minimal latency
- Token usage metering via Azure Monitor for cost tracking

**Cons:**
- Azure OpenAI quota limits may require capacity planning (Open Question #1)
- Prompt engineering requires iterative tuning for checklist generation quality

---

### Option 2: OpenAI API Direct (ChatGPT)

**Description:** Use the OpenAI commercial API directly.

**Pros:**
- Potentially faster access to newest model versions

**Cons:**
- **BLOCKED by enterprise standards and NFR-009** — data leaves the corporate
  Azure tenant
- Procurement policy prohibits direct OpenAI contracts
- No data residency guarantee

---

### Option 3: Self-hosted open-source LLM on AKS

**Description:** Deploy an open-source LLM (e.g., Llama, Mistral) on AKS
with GPU nodes.

**Pros:**
- Full control over model and data
- No per-token API costs

**Cons:**
- **Violates PaaS-first policy** — requires AKS with GPU node pools
- Significant operational overhead for model serving (vLLM, TGI)
- Open-source models underperform GPT-4o on complex policy Q&A tasks
- GPU node pool costs likely exceed Azure OpenAI API costs at this query volume
- No built-in content filtering

---

## RAG Pipeline Architecture

```
┌─────────────┐     ┌───────────────────┐     ┌──────────────────┐
│  Employee    │────▶│  FastAPI Chat API  │────▶│  Intent          │
│  (Teams/Web) │     │                   │     │  Classifier      │
└─────────────┘     └───────────────────┘     └──────┬───────────┘
                                                      │
                            ┌─────────────────────────┤
                            ▼                         ▼
                    ┌───────────────┐         ┌──────────────────┐
                    │ Confidential  │         │ Azure AI Search  │
                    │ Topic Filter  │         │ (hybrid query)   │
                    │ → Escalate    │         └──────┬───────────┘
                    └───────────────┘                │ top-k chunks
                                                    ▼
                                            ┌──────────────────┐
                                            │ Prompt Assembly   │
                                            │ (system prompt +  │
                                            │  retrieved chunks +│
                                            │  user query +     │
                                            │  conversation     │
                                            │  history)         │
                                            └──────┬───────────┘
                                                    ▼
                                            ┌──────────────────┐
                                            │ Azure OpenAI     │
                                            │ GPT-4o           │
                                            │ (chat completion)│
                                            └──────┬───────────┘
                                                    │
                                                    ▼
                                            ┌──────────────────┐
                                            │ Response Parser  │
                                            │ - Answer text    │
                                            │ - Citations      │
                                            │ - Checklist      │
                                            │ - Disclaimer     │
                                            └──────────────────┘
```

### Key Design Decisions

1. **Embedding model:** `text-embedding-3-large` (1536 dimensions) deployed
   in Azure OpenAI. Used for both document chunk embedding (at ingestion) and
   query embedding (at query time).

2. **Chat model:** GPT-4o (or GPT-4o-mini for cost-sensitive admin test
   queries). Model version selection is parameterized — Open Question #1.

3. **Retrieval strategy:** Hybrid search in Azure AI Search combining:
   - Vector similarity search (cosine) against chunk embeddings
   - BM25 keyword search against chunk text
   - Semantic ranker for re-ranking the merged results
   - Top-k = 5 chunks per query (tunable)

4. **Grounding enforcement:** System prompt instructs the model to:
   - Only answer from the provided context chunks
   - Include `[Source: {doc_title}, §{section}, effective {date}]` citations
   - Return `"NO_RELEVANT_POLICY"` token if no chunk is relevant → triggers
     the "I wasn't able to find a policy" response (FR-014)
   - Return structured JSON for checklist responses with `assisted`/`manual`
     classification per step (FR-017–FR-020)

5. **Conversation context:** Last N messages stored in Azure Cache for Redis
   (session-scoped, 90-day TTL). Passed as conversation history in the chat
   completion request (FR-009).

6. **Confidential topic detection:** Pre-retrieval classifier checks the user
   query against a list of sensitive topic patterns. If triggered, the RAG
   pipeline is bypassed entirely and an escalation response is returned (FR-016).

7. **LLM fallback mode:** When Azure OpenAI is unreachable, the system queries
   Azure AI Search using BM25 keyword search only and returns raw search results
   labeled as "basic search result, not a full answer" (NFR-006).

---

## Consequences

### Positive
- Fully governance-compliant RAG pipeline with no external dependencies
- Hybrid search provides both semantic retrieval (normal mode) and keyword
  fallback (LLM outage mode) from a single index
- Structured prompt templates enforce citation and checklist formatting
- Azure OpenAI content filtering adds a safety layer beyond the custom
  confidential topic detector

### Negative / Trade-offs
- Per-token API costs for Azure OpenAI (mitigated: GPT-4o-mini for lower-value
  queries, response caching for frequently asked questions)
- Prompt engineering is iterative and requires tuning during content loading phase
- Retrieval quality depends on chunking strategy — requires experimentation

### Risks
- Azure OpenAI quota exhaustion at peak load — mitigated by capacity planning
  (Open Question #1) and rate limiting in the API gateway
- Chunking strategy may not preserve table/list structure well for all 140
  documents — mitigated by UAT review with policy team
- GPT-4o may occasionally produce verbose responses — mitigated by prompt
  constraints and response length limits

---

## Implementation Notes

- Use `azure-ai-openai` Python SDK (async client) for both embeddings and chat completion
- Use `azure-search-documents` Python SDK for index management and hybrid queries
- System prompts stored as Jinja2 templates in `app/prompts/` directory
- Response parsing: structured output mode (JSON schema) for checklist responses;
  text mode with citation regex extraction for factual answers
- Rate limiting: token bucket per user in Azure Cache for Redis
- Caching: hash-based cache for identical queries within 1-hour window
- All LLM calls instrumented with OpenTelemetry spans → Application Insights

---

## References
- `governance/enterprise-standards.md` — Observability Requirements, Security Policy
- Requirements GOV-002 flag: ChatGPT direct API blocked
- Related: ADR-0007 (language), ADR-0009 (data storage)
- Related requirements: FR-008, FR-009, FR-012–FR-016, FR-017–FR-021, NFR-006,
  NFR-009, NFR-015, NFR-016
