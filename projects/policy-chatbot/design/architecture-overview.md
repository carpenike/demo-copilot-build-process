# Architecture Overview: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-20
> **Produced by:** Design Agent
> **Input:** `projects/policy-chatbot/requirements/requirements.md`
> **Related ADRs:** ADR-0007 through ADR-0012

---

## 1. System Context Diagram (C4 Level 1)

Shows the Policy Chatbot system in the context of its external actors and
systems.

```mermaid
C4Context
    title System Context — Policy Chatbot

    Person(employee, "Employee", "~8,000 employees across 12 offices")
    Person(admin, "Policy Administrator", "HR/IT staff managing policy documents")

    System(chatbot, "Policy Chatbot", "Conversational AI that answers policy questions with citations and next-step checklists")

    System_Ext(teams, "Microsoft Teams", "Employee messaging platform")
    System_Ext(intranet, "Corporate Intranet", "Web portal with embedded chat widget")
    System_Ext(sharepoint, "SharePoint Online", "Policy document repository")
    System_Ext(servicenow, "ServiceNow", "IT/HR ticketing system for escalations")
    System_Ext(entra, "Microsoft Entra ID", "Corporate identity provider (SSO)")
    System_Ext(graph, "Microsoft Graph API", "Employee profile and directory data")
    System_Ext(campusmap, "Campus Map System", "Wayfinding and location data")

    Rel(employee, teams, "Asks policy questions via")
    Rel(employee, intranet, "Asks policy questions via")
    Rel(admin, chatbot, "Manages documents, views analytics")
    Rel(chatbot, teams, "Receives/sends messages via Bot Framework")
    Rel(chatbot, intranet, "Serves web chat widget")
    Rel(chatbot, sharepoint, "Pulls policy documents from")
    Rel(chatbot, servicenow, "Creates escalation tickets via API")
    Rel(chatbot, entra, "Authenticates users via OIDC")
    Rel(chatbot, graph, "Retrieves employee profiles")
    Rel(chatbot, campusmap, "Retrieves wayfinding data")
```

---

## 2. Container Diagram (C4 Level 2)

Shows the containers (deployable units) within the Policy Chatbot system.

```mermaid
C4Container
    title Container Diagram — Policy Chatbot

    Person(employee, "Employee")
    Person(admin, "Policy Administrator")

    System_Boundary(chatbot_system, "Policy Chatbot System") {
        Container(api, "API Service", "Python / FastAPI", "Handles chat, admin, and analytics requests. Orchestrates RAG pipeline.")
        Container(ingestion_job, "Ingestion Job", "Python / ACA Job", "Syncs documents from SharePoint/CMS to Blob Storage. Triggers on-demand or scheduled.")

        ContainerDb(postgres, "PostgreSQL", "Azure Database for PostgreSQL", "Documents, conversations, messages, feedback, analytics, users")
        ContainerDb(redis, "Redis", "Azure Cache for Redis", "Active conversation session context")
        ContainerDb(blob, "Blob Storage", "Azure Blob Storage", "Raw policy document files (PDF, DOCX, HTML)")
        ContainerDb(search, "AI Search", "Azure AI Search", "Chunked + embedded policy content index")
        Container(openai, "Azure OpenAI", "GPT-4o + text-embedding-ada-002", "Intent classification, answer generation, embedding generation")
    }

    System_Ext(entra, "Microsoft Entra ID")
    System_Ext(teams, "Microsoft Teams")
    System_Ext(servicenow, "ServiceNow")
    System_Ext(graph, "Microsoft Graph")
    System_Ext(sharepoint, "SharePoint Online")
    System_Ext(campusmap, "Campus Map System")

    Rel(employee, api, "Sends chat messages via Teams Bot / Web Widget", "HTTPS")
    Rel(admin, api, "Manages documents, views analytics", "HTTPS")
    Rel(api, postgres, "Reads/writes application data", "TCP/SSL")
    Rel(api, redis, "Reads/writes session context", "TCP/SSL")
    Rel(api, search, "Hybrid search queries", "HTTPS")
    Rel(api, openai, "Intent classification + answer generation", "HTTPS")
    Rel(api, blob, "Uploads documents", "HTTPS")
    Rel(api, entra, "Validates JWT tokens", "HTTPS")
    Rel(api, graph, "Retrieves user profiles", "HTTPS")
    Rel(api, servicenow, "Creates escalation tickets", "HTTPS")
    Rel(api, campusmap, "Retrieves location data", "HTTPS")
    Rel(ingestion_job, sharepoint, "Pulls documents", "HTTPS")
    Rel(ingestion_job, blob, "Uploads to blob storage", "HTTPS")
    Rel(blob, search, "AI Search indexer reads from blob", "Internal")
    Rel(search, openai, "Embedding generation via skillset", "HTTPS")
```

---

## 3. Component Diagram (C4 Level 3) — API Service

Shows the internal structure of the FastAPI API Service container.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FastAPI API Service                             │
│                                                                         │
│  ┌─────────────────────┐   ┌─────────────────────┐                     │
│  │   Auth Middleware    │   │  OpenTelemetry       │                     │
│  │  (JWT validation,   │   │  Middleware           │                     │
│  │   role extraction)  │   │  (traces, metrics)    │                     │
│  └────────┬────────────┘   └─────────────────────┘                     │
│           │                                                              │
│  ┌────────▼────────────────────────────────────────────────────────┐    │
│  │                        API Routers                               │    │
│  │                                                                  │    │
│  │  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌───────────┐  │    │
│  │  │ Chat     │  │ Admin        │  │ Analytics │  │ Health    │  │    │
│  │  │ Router   │  │ Router       │  │ Router    │  │ Router    │  │    │
│  │  │          │  │              │  │           │  │           │  │    │
│  │  │ POST     │  │ CRUD         │  │ GET       │  │ GET       │  │    │
│  │  │ /chat    │  │ /documents   │  │ /summary  │  │ /health   │  │    │
│  │  │ POST     │  │ POST         │  │ GET       │  │ GET       │  │    │
│  │  │ /escalate│  │ /reindex     │  │ /intents  │  │ /ready    │  │    │
│  │  │ GET      │  │ POST         │  │ GET       │  │           │  │    │
│  │  │ /convo   │  │ /test-query  │  │ /unans.   │  │           │  │    │
│  │  │ POST     │  │ GET          │  │ GET       │  │           │  │    │
│  │  │ /feedback│  │ /coverage    │  │ /flagged  │  │           │  │    │
│  │  └────┬─────┘  └──────┬──────┘  └─────┬─────┘  └───────────┘  │    │
│  └───────┼───────────────┼────────────────┼────────────────────────┘    │
│          │               │                │                              │
│  ┌───────▼───────────────▼────────────────▼────────────────────────┐    │
│  │                      Service Layer                               │    │
│  │                                                                  │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │    │
│  │  │ ChatService      │  │ DocumentService  │  │ Analytics    │  │    │
│  │  │                  │  │                  │  │ Service      │  │    │
│  │  │ - orchestrate()  │  │ - upload()       │  │              │  │    │
│  │  │ - classify_intent│  │ - reindex()      │  │ - summary()  │  │    │
│  │  │ - retrieve()     │  │ - retire()       │  │ - intents()  │  │    │
│  │  │ - generate()     │  │ - get_versions() │  │ - unanswered │  │    │
│  │  │ - format_answer()│  │ - test_query()   │  │ - flagged()  │  │    │
│  │  │ - escalate()     │  │ - coverage()     │  │              │  │    │
│  │  └──────┬───────────┘  └────────┬─────────┘  └──────┬───────┘  │    │
│  └─────────┼───────────────────────┼───────────────────┼───────────┘    │
│            │                       │                   │                  │
│  ┌─────────▼───────────────────────▼───────────────────▼───────────┐    │
│  │                      Integration Clients                         │    │
│  │                                                                  │    │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────┐   │    │
│  │  │ OpenAI     │ │ AI Search  │ │ Blob     │ │ ServiceNow   │   │    │
│  │  │ Client     │ │ Client     │ │ Client   │ │ Client       │   │    │
│  │  └────────────┘ └────────────┘ └──────────┘ └──────────────┘   │    │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────┐                    │    │
│  │  │ PostgreSQL │ │ Redis      │ │ Graph    │                    │    │
│  │  │ Client     │ │ Client     │ │ Client   │                    │    │
│  │  └────────────┘ └────────────┘ └──────────┘                    │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Deployment Diagram

Shows how containers map to Azure infrastructure.

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Azure Resource Group: rg-policy-chatbot-dev      │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │             Azure Container Apps Environment                   │  │
│  │                                                                │  │
│  │  ┌──────────────────────┐   ┌────────────────────────────┐    │  │
│  │  │  ACA App:            │   │  ACA Job:                   │    │  │
│  │  │  policy-chatbot-api  │   │  policy-chatbot-ingestion   │    │  │
│  │  │                      │   │                              │    │  │
│  │  │  Image: ACR/         │   │  Image: ACR/                │    │  │
│  │  │   policy-chatbot:    │   │   policy-chatbot-ingestion: │    │  │
│  │  │   latest             │   │   latest                    │    │  │
│  │  │                      │   │                              │    │  │
│  │  │  Replicas: 2–10      │   │  Trigger: manual/cron       │    │  │
│  │  │  Ingress: external   │   │  Execution: single          │    │  │
│  │  │  (HTTPS, port 8000)  │   │                              │    │  │
│  │  │                      │   │                              │    │  │
│  │  │  Scaling:            │   │                              │    │  │
│  │  │   HTTP concurrent    │   │                              │    │  │
│  │  │   requests = 50      │   │                              │    │  │
│  │  └──────────┬───────────┘   └──────────────┬───────────────┘    │  │
│  │             │ Managed Identity              │ Managed Identity   │  │
│  └─────────────┼──────────────────────────────┼────────────────────┘  │
│                │                               │                      │
│  ┌─────────────▼───────────────────────────────▼──────────────────┐  │
│  │                    Azure PaaS Services                          │  │
│  │                                                                 │  │
│  │  ┌─────────────────┐  ┌───────────────┐  ┌─────────────────┐  │  │
│  │  │ Azure Database  │  │ Azure Cache   │  │ Azure Blob      │  │  │
│  │  │ for PostgreSQL  │  │ for Redis     │  │ Storage         │  │  │
│  │  │ Flexible Server │  │               │  │                 │  │  │
│  │  │                 │  │ SKU: Basic C1 │  │ Containers:     │  │  │
│  │  │ SKU: GP 2vCores │  │ 250MB cache   │  │  policy-docs    │  │  │
│  │  │ PG 16           │  │               │  │  extracted-text │  │  │
│  │  └─────────────────┘  └───────────────┘  └─────────────────┘  │  │
│  │                                                                 │  │
│  │  ┌─────────────────┐  ┌───────────────────────────────────┐    │  │
│  │  │ Azure AI Search │  │ Azure OpenAI Service              │    │  │
│  │  │                 │  │                                    │    │  │
│  │  │ SKU: Standard   │  │ Deployments:                      │    │  │
│  │  │ Index:          │  │  gpt-4o (chat completion)         │    │  │
│  │  │  policy-chunks  │  │  text-embedding-ada-002 (embed)   │    │  │
│  │  │                 │  │                                    │    │  │
│  │  │ Indexer:        │  │ Data residency: same region       │    │  │
│  │  │  blob-indexer   │  │ Abuse monitoring: opt-out         │    │  │
│  │  └─────────────────┘  └───────────────────────────────────┘    │  │
│  │                                                                 │  │
│  │  ┌─────────────────┐  ┌───────────────────────────────────┐    │  │
│  │  │ Azure Key Vault │  │ Azure Container Registry (ACR)    │    │  │
│  │  │                 │  │                                    │    │  │
│  │  │ Secrets:        │  │ Repository:                        │    │  │
│  │  │  (Entra ID      │  │  policy-chatbot                   │    │  │
│  │  │   client secret)│  │  policy-chatbot-ingestion          │    │  │
│  │  └─────────────────┘  └───────────────────────────────────┘    │  │
│  │                                                                 │  │
│  │  ┌─────────────────────────────────────────────────────────┐    │  │
│  │  │ Azure Monitor / Application Insights                    │    │  │
│  │  │                                                         │    │  │
│  │  │ - Structured JSON logs from ACA → Log Analytics        │    │  │
│  │  │ - OpenTelemetry traces → Application Insights          │    │  │
│  │  │ - Custom metrics: response latency, token usage,       │    │  │
│  │  │   retrieval recall, confidence scores                   │    │  │
│  │  │ - Alert rules: latency > 5s, error rate > 5%,          │    │  │
│  │  │   LLM availability < 99%                                │    │  │
│  │  └─────────────────────────────────────────────────────────┘    │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 5. Request Flow — Chat Query

Sequence of operations when an employee asks a policy question:

```mermaid
sequenceDiagram
    participant U as Employee
    participant API as FastAPI (ACA)
    participant Auth as Entra ID
    participant Redis as Azure Redis
    participant Search as AI Search
    participant LLM as Azure OpenAI
    participant PG as PostgreSQL

    U->>API: POST /v1/chat {message, conversation_id?}
    API->>Auth: Validate JWT token
    Auth-->>API: Token valid, claims: {name, role, dept, location}

    alt New conversation
        API->>PG: Create conversation record
        API->>Redis: Create session:{conv_id}
    else Existing conversation
        API->>Redis: Load session:{conv_id} (last 10 messages)
    end

    Note over API: Step 1 — Intent Classification
    API->>LLM: Classify intent (factual/procedural/wayfinding/confidential/escalation)
    LLM-->>API: Intent: procedural, domain: HR, confidence: 0.91

    alt Confidential topic detected
        API-->>U: Confidential escalation response (no LLM answer)
    end

    Note over API: Step 2 — Retrieval
    API->>Search: Hybrid query (vector + keyword) with category filter
    Search-->>API: Top-10 ranked chunks with metadata

    Note over API: Step 3 — Generation
    API->>LLM: Generate answer from chunks + conversation context + system prompt
    LLM-->>API: Grounded answer with citations

    Note over API: Step 4 — Post-processing
    API->>API: Format response (citations, checklist, disclaimer)
    API->>PG: Store user message + assistant message
    API->>Redis: Update session:{conv_id} with new messages

    API-->>U: Response with answer, citations, disclaimer
```

---

## 6. Request Flow — Document Upload and Indexing

```mermaid
sequenceDiagram
    participant Admin as Administrator
    participant API as FastAPI (ACA)
    participant PG as PostgreSQL
    participant Blob as Azure Blob Storage
    participant Indexer as AI Search Indexer
    participant Search as AI Search Index
    participant LLM as Azure OpenAI (Embeddings)

    Admin->>API: POST /v1/admin/documents (file + metadata)
    API->>API: Validate file type, size, metadata
    API->>Blob: Upload file to policy-documents/{category}/{id}/{version}.ext
    API->>PG: Insert document record + version record
    API->>Indexer: Trigger indexer run via REST API

    Indexer->>Blob: Read new/changed blobs
    Indexer->>Indexer: Document cracking (PDF/DOCX/HTML → text)
    Indexer->>Indexer: Text splitting (512-token chunks, 50-token overlap)
    Indexer->>LLM: Generate embeddings for each chunk
    LLM-->>Indexer: 1536-dim vectors
    Indexer->>Search: Populate policy-chunks index

    API->>PG: Update document.last_indexed_at
    API-->>Admin: 201 Created {id, indexing_status: "in_progress"}
```

---

## 7. Security Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                      Internet / Corporate Network                │
│                                                                  │
│  Employees ──── Teams / Intranet ──── HTTPS ────┐               │
│  Admins ───── Admin Console ──────── HTTPS ─────┤               │
│                                                  │               │
│  ┌───────────────────────────────────────────────▼────────────┐  │
│  │              Azure Virtual Network (optional)              │  │
│  │                                                            │  │
│  │  ┌──────────────────┐     TLS 1.2+                        │  │
│  │  │  ACA Ingress     │◄══════════════════════               │  │
│  │  │  (public HTTPS)  │                                      │  │
│  │  │  JWT validation  │                                      │  │
│  │  └────────┬─────────┘                                      │  │
│  │           │ Managed Identity (no secrets in code)          │  │
│  │           │                                                 │  │
│  │  ┌────────▼──────────────────────────────────────────────┐ │  │
│  │  │  Azure PaaS Services                                  │ │  │
│  │  │  (PostgreSQL, Redis, Blob, AI Search, OpenAI)         │ │  │
│  │  │                                                        │ │  │
│  │  │  - Private endpoints (recommended for production)      │ │  │
│  │  │  - Managed Identity RBAC — no connection strings       │ │  │
│  │  │  - Encryption at rest (AES-256) on all data stores     │ │  │
│  │  │  - Encryption in transit (TLS 1.2+) on all connections │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  │                                                            │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │  Azure Key Vault                                       │ │  │
│  │  │  - Entra ID client secret                              │ │  │
│  │  │  - No secrets in env vars, code, or config             │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Key security controls:**
- All user access authenticated via Entra ID OIDC (NFR-007)
- RBAC enforced at API layer — Employee vs Admin roles (NFR-010)
- Managed Identity for all service-to-service authentication — zero secrets in code
- TLS 1.2+ on all connections (NFR-011)
- AES-256 encryption at rest on PostgreSQL, Redis, and Blob Storage (NFR-012)
- 90-day data retention with automated purge (NFR-008)
- Employee queries never leave Azure tenant boundary (NFR-009)
- No `allow_origins=["*"]` — CORS origins explicitly listed per enterprise standard

---

## 8. Technology Summary

| Component | Technology | ADR |
|-----------|-----------|-----|
| Language | Python 3.11+ | ADR-0007 |
| Framework | FastAPI | ADR-0007 |
| Compute | Azure Container Apps | ADR-0008 |
| Relational DB | Azure Database for PostgreSQL Flexible Server | ADR-0009 |
| Cache | Azure Cache for Redis | ADR-0009 |
| Object storage | Azure Blob Storage | ADR-0009 |
| Search | Azure AI Search (hybrid: vector + keyword) | ADR-0010 |
| LLM | Azure OpenAI GPT-4o | ADR-0010 |
| Embeddings | Azure OpenAI text-embedding-ada-002 | ADR-0010 |
| Document ingestion | AI Search indexer + blob data source | ADR-0011 |
| Authentication | Microsoft Entra ID (OIDC / OAuth 2.0) | ADR-0012 |
| Observability | OpenTelemetry SDK → Azure Monitor / Application Insights | Enterprise standard |
| IaC | Bicep | Enterprise standard |
| CI/CD | GitHub Actions | Enterprise standard |
| Container registry | Azure Container Registry | Enterprise standard |
| Secrets | Azure Key Vault | Enterprise standard |
