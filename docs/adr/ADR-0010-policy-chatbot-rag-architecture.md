# ADR-0010: Policy Chatbot — RAG Architecture

> **Status:** Accepted
> **Date:** 2026-03-20
> **Deciders:** Platform Engineering, HR Service Desk Manager
> **Project:** policy-chatbot

---

## Context

The Policy Chatbot must generate answers grounded exclusively in indexed policy
content (FR-012) with source citations (FR-013) and zero hallucination
(NFR-016). It must classify user intent (FR-008), maintain conversation context
(FR-009), detect confidential topics (FR-016), and fall back gracefully when
the LLM is unavailable (NFR-006).

Enterprise standards require Azure-hosted AI services with guaranteed data
residency (NFR-009) and prohibit external LLM training on employee data.

This ADR defines the retrieval-augmented generation (RAG) pipeline architecture.

---

## Decision

> We will use **Azure AI Search** for semantic retrieval and **Azure OpenAI
> Service (GPT-4o)** for answer generation in a RAG pipeline because they
> provide enterprise-grade search and LLM capabilities within the Azure tenant
> boundary, meeting data residency and grounding requirements.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| AI service | Corporate-tenant-hosted, data residency (NFR-009) | Azure OpenAI Service | ✅ |
| Search | Azure PaaS preferred | Azure AI Search | ✅ |
| Observability | OpenTelemetry + Azure Monitor | OTel SDK + Azure Monitor exporter | ✅ |
| No external training | NFR-009 | Azure OpenAI abuse monitoring opt-out | ✅ |

---

## Options Considered

### Option 1: Azure AI Search + Azure OpenAI (GPT-4o) ← Chosen

**Description:** A two-stage RAG pipeline: (1) Azure AI Search performs hybrid
retrieval (vector + keyword) over the indexed policy corpus, (2) Azure OpenAI
GPT-4o generates a grounded answer from the top-K retrieved chunks with a
system prompt enforcing citation and grounding rules.

**Pros:**
- Azure AI Search provides hybrid search (semantic ranking + BM25 keyword) for
  high recall across both natural language and exact policy terms
- Azure OpenAI is deployed within the corporate Azure tenant — employee queries
  never leave the tenant boundary (NFR-009)
- Built-in semantic ranker re-ranks results for relevance before passing to LLM
- GPT-4o has a 128K context window — can include many policy chunks plus
  conversation history for follow-up resolution (FR-009)
- Azure AI Search supports document cracking (PDF/DOCX extraction) via built-in
  skillsets — can be used as part of the ingestion pipeline
- Data residency guaranteed by Azure region deployment

**Cons:**
- Azure AI Search and Azure OpenAI have per-query costs that scale with usage
- GPT-4o latency (~1–3s) consumes a significant portion of the 5-second SLA budget
- Requires careful prompt engineering to prevent hallucination

---

### Option 2: PostgreSQL pgvector + Azure OpenAI

**Description:** Store embeddings in PostgreSQL using the pgvector extension and
perform vector similarity search directly in the database.

**Pros:**
- Single database for both structured data and vector search — simpler architecture
- No additional search service cost
- Full SQL control over retrieval filters

**Cons:**
- pgvector lacks semantic ranking — only vector cosine similarity, no hybrid
  BM25 + vector fusion
- Inferior retrieval quality for policy documents that contain exact terminology
  (e.g., "FMLA", "ADA", "Section 4.2.1") where keyword matching is critical
- No built-in document cracking or enrichment pipeline
- Scaling vector search on PostgreSQL requires careful index tuning; AI Search
  handles this natively
- Weaker relevance for the 85% accuracy target (NFR-015)

---

### Option 3: Self-hosted Elasticsearch + Azure OpenAI

**Description:** Deploy Elasticsearch on AKS for search, Azure OpenAI for generation.

**Pros:**
- Full control over search configuration and ranking algorithms
- Strong hybrid search capabilities

**Cons:**
- Self-managed Elasticsearch on AKS violates the Azure PaaS-first policy
- Significant operational overhead — cluster management, upgrades, scaling
- No Managed Identity integration — requires separate credential management
- Azure AI Search provides equivalent functionality as a managed service

---

## RAG Pipeline Design

```
┌──────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│  User    │────▶│  FastAPI      │────▶│  Azure AI     │────▶│  Azure OpenAI │
│  Query   │     │  Orchestrator │     │  Search       │     │  GPT-4o       │
└──────────┘     └──────┬───────┘     └───────────────┘     └──────┬───────┘
                        │                                          │
                        │  1. Intent classification                │
                        │  2. Confidential topic check             │
                        │  3. Retrieve top-K chunks                │
                        │  4. Construct grounded prompt            │
                        │  5. Generate answer + citations  ◀───────┘
                        │  6. Format response with disclaimer
                        ▼
                 ┌──────────────┐
                 │  Response    │
                 │  + Citations │
                 │  + Disclaimer│
                 └──────────────┘
```

### Pipeline Steps

1. **Intent Classification** — GPT-4o classifies the query as: factual,
   procedural, wayfinding, escalation, or confidential (FR-008, FR-016)
2. **Confidential Check** — if intent is confidential, skip RAG and return
   escalation response immediately (FR-016)
3. **Retrieval** — Azure AI Search hybrid query (vector + keyword) returns
   top-10 chunks with metadata (document title, section, effective date)
4. **Prompt Construction** — system prompt enforces grounding rules:
   - Answer ONLY from the provided context chunks
   - Include citation for every claim
   - If no relevant context found, say so (FR-014)
   - Always append the legal disclaimer (FR-015)
5. **Generation** — GPT-4o generates the answer with structured citations
6. **Post-processing** — extract citations, format checklist if procedural
   (FR-017–FR-020), append disclaimer

### Fallback Behavior (NFR-006)

If Azure OpenAI is unavailable, the orchestrator falls back to:
1. Azure AI Search keyword-only query
2. Return top-3 matching policy sections as "basic search results"
3. Clearly indicate: "This is a basic search result, not a full answer.
   The AI assistant is temporarily unavailable."

---

## Consequences

### Positive
- Hybrid retrieval (vector + keyword) maximizes recall for both natural language
  and specific policy terminology
- Azure-tenant-hosted LLM meets all data residency and privacy requirements
- Semantic ranker improves precision before LLM processing
- Built-in fallback path for LLM outages

### Negative / Trade-offs
- Per-query cost for both AI Search and Azure OpenAI — must monitor and budget
- 1–3s LLM latency leaves limited budget for other processing within the 5s SLA
- Prompt engineering requires iteration and testing to achieve 85% accuracy target

### Risks
- Hallucination despite grounding instructions — mitigated by strict system
  prompt, low temperature (0.1), and UAT testing against 200 queries (NFR-015, NFR-016)
- Azure OpenAI quota limits — mitigated by provisioned throughput (PTU) or
  standard deployment with retry logic
- Context window overflow with large policy documents — mitigated by chunking
  strategy in ADR-0011

---

## Implementation Notes

- **Azure AI Search index:** `policy-chunks` index with fields: `chunk_id`,
  `content`, `content_vector`, `document_id`, `document_title`, `section_heading`,
  `category`, `effective_date`, `source_url`
- **Embedding model:** `text-embedding-ada-002` (1536 dimensions) deployed on
  Azure OpenAI — same tenant
- **Completion model:** `gpt-4o` deployed on Azure OpenAI with temperature=0.1
- **Chunking:** 512-token chunks with 50-token overlap (details in ADR-0011)
- **Conversation history:** include last 5 message pairs from Redis session
  context in the prompt for follow-up resolution (FR-009)
- **SDKs:** `azure-search-documents`, `openai` (Azure-configured), `tiktoken`
  for token counting
- **Tracing:** OpenTelemetry spans for each pipeline stage — intent classification,
  retrieval, generation — exported to Application Insights

---

## References
- [Azure AI Search](https://learn.microsoft.com/en-us/azure/search/)
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [RAG patterns](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview)
- Related requirements: FR-008, FR-009, FR-012, FR-013, FR-014, FR-015, FR-016, NFR-001, NFR-006, NFR-009, NFR-015, NFR-016
- Related ADRs: ADR-0007 (language), ADR-0009 (data storage), ADR-0011 (document ingestion)
