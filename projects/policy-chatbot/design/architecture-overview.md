# Architecture Overview: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-17
> **Produced by:** Design Agent
> **Related ADRs:** ADR-0007, ADR-0008, ADR-0009, ADR-0010, ADR-0011

---

## System Context Diagram

```mermaid
graph TB
    subgraph External Actors
        EMP[Employee]
        ADMIN[Policy Administrator]
    end

    subgraph External Systems
        TEAMS[Microsoft Teams]
        INTRANET[Corporate Intranet]
        SHAREPOINT[SharePoint Online]
        SERVICENOW[ServiceNow ITSM]
        WORKDAY[Workday]
        GRAPH[Microsoft Graph API]
        CAMPUS_MAP[Campus Map System]
    end

    subgraph Enterprise Boundary
        subgraph Azure Container Apps
            API[Policy Chatbot API<br/>FastAPI]
            WORKER[Celery Workers<br/>Document Indexing]
            BOT[Bot Service Handler<br/>Bot Framework SDK]
        end

        subgraph Azure AI Services
            AOAI[Azure OpenAI Service<br/>GPT-4o / GPT-4o-mini]
            AI_SEARCH[Azure AI Search<br/>Vector + Keyword Index]
        end

        subgraph Azure Data Services
            PG[(Azure Database for<br/>PostgreSQL)]
            REDIS[(Azure Cache<br/>for Redis)]
            BLOB[(Azure Blob<br/>Storage)]
        end

        subgraph Azure Platform Services
            KV[Azure Key Vault]
            ACR[Azure Container<br/>Registry]
            MONITOR[Azure Monitor /<br/>Application Insights]
            BOT_SVC[Azure Bot Service]
            ENTRA[Microsoft Entra ID]
        end
    end

    EMP -->|Chat via Teams| TEAMS
    EMP -->|Chat via web widget| INTRANET
    ADMIN -->|Upload docs, analytics| INTRANET

    TEAMS --> BOT_SVC --> BOT
    INTRANET -->|Direct Line| BOT_SVC
    INTRANET -->|Admin API| API

    BOT --> API
    API --> AOAI
    API --> AI_SEARCH
    API --> PG
    API --> REDIS
    API --> BLOB
    API --> GRAPH
    API --> SERVICENOW
    API --> CAMPUS_MAP

    WORKER --> AI_SEARCH
    WORKER --> AOAI
    WORKER --> BLOB
    WORKER --> PG
    WORKER --> REDIS

    API --> KV
    API --> MONITOR
    WORKER --> MONITOR
    API --> ENTRA
    BOT --> ENTRA

    ADMIN -->|Upload policy docs| BLOB
    SHAREPOINT -->|Ingest policies| WORKER
```

---

## Component Diagram

```mermaid
graph LR
    subgraph Policy Chatbot API - FastAPI
        direction TB
        HEALTH[Health Endpoints<br/>/health, /ready]
        AUTH_MW[Auth Middleware<br/>Entra ID JWT]
        BOT_EP[Bot Messages Endpoint<br/>/api/messages]
        CHAT_EP[Chat API<br/>/api/v1/chat]
        ADMIN_EP[Admin API<br/>/api/admin]
        ANALYTICS_EP[Analytics API<br/>/api/admin/analytics]

        subgraph Core Services
            INTENT[Intent Classifier]
            RAG[RAG Pipeline]
            CHECKLIST[Checklist Generator]
            ESCALATION[Escalation Manager]
            CITATION[Citation Extractor]
            SENSITIVE[Sensitive Topic Detector]
        end

        subgraph Data Services
            DOC_SVC[Document Service]
            CONV_SVC[Conversation Service]
            FEEDBACK_SVC[Feedback Service]
            PROFILE_SVC[Employee Profile Service]
            SEARCH_SVC[Search Service]
            INDEX_SVC[Indexing Service]
        end
    end

    BOT_EP --> INTENT
    CHAT_EP --> INTENT
    INTENT --> SENSITIVE
    INTENT --> RAG
    RAG --> SEARCH_SVC
    RAG --> CITATION
    RAG --> CHECKLIST
    RAG --> ESCALATION
    ADMIN_EP --> DOC_SVC
    ADMIN_EP --> INDEX_SVC
    ANALYTICS_EP --> FEEDBACK_SVC
    CHAT_EP --> CONV_SVC
    CHAT_EP --> PROFILE_SVC
```

---

## Component Descriptions

### Policy Chatbot API (FastAPI)

The primary application, deployed as an Azure Container App. Handles all HTTP
traffic including Bot Framework messages, REST API requests, and admin console
API calls.

| Component | Purpose | FR Coverage |
|-----------|---------|-------------|
| Bot Messages Endpoint | Receives Teams/web chat messages via Bot Framework | FR-007 |
| Chat API | REST endpoints for direct chat integration | FR-007 |
| Admin API | Document management, test queries, coverage reports | FR-005, FR-031–FR-033 |
| Analytics API | Usage metrics, satisfaction scores, unanswered queries | FR-029, FR-030 |
| Intent Classifier | Determines policy domain and query type | FR-008 |
| Sensitive Topic Detector | Identifies confidential HR queries and blocks AI answers | FR-016 |
| RAG Pipeline | Retrieves policy chunks and generates grounded answers | FR-012–FR-014 |
| Citation Extractor | Extracts and validates source citations from LLM output | FR-013 |
| Checklist Generator | Produces step-by-step checklists for procedural queries | FR-017–FR-021 |
| Escalation Manager | Handles manual and automatic escalation to live agents | FR-025–FR-027 |
| Document Service | CRUD operations for policy documents and metadata | FR-001, FR-004, FR-006 |
| Indexing Service | Triggers document chunking, embedding, and AI Search indexing | FR-002, FR-003, FR-005 |
| Conversation Service | Manages conversation context and history | FR-009, NFR-008 |
| Feedback Service | Records feedback, flags repeated negative feedback | FR-028, FR-030 |
| Employee Profile Service | Retrieves and caches employee profile from Graph API | FR-011 |
| Search Service | Interfaces with Azure AI Search for hybrid retrieval | FR-012 |

### Celery Workers

Background workers deployed as a separate Azure Container App, processing
document indexing tasks asynchronously.

| Task | Purpose | FR Coverage |
|------|---------|-------------|
| `ingest_document` | Parse, chunk, embed, and index a single document | FR-001–FR-003 |
| `reindex_corpus` | Full corpus re-indexing | FR-005, NFR-003 |
| `cleanup_conversations` | Purge conversation logs older than 90 days | NFR-008 |

### Azure Bot Service

Microsoft-managed service that routes messages between Teams/web chat clients and
the chatbot API. Handles protocol translation and channel-specific formatting.

---

## Data Flow Diagrams

### Chat Query Flow

```mermaid
sequenceDiagram
    participant E as Employee
    participant T as Teams / Web Chat
    participant BS as Azure Bot Service
    participant API as Chatbot API
    participant R as Redis
    participant CLS as Intent Classifier
    participant AIS as Azure AI Search
    participant AOI as Azure OpenAI
    participant PG as PostgreSQL

    E->>T: "What is the bereavement leave policy?"
    T->>BS: Activity message
    BS->>API: POST /api/messages
    API->>R: Load conversation context
    API->>CLS: Classify intent (GPT-4o-mini)
    CLS-->>API: domain=HR, type=factual, sensitive=false
    API->>AIS: Hybrid search (vector + keyword)
    AIS-->>API: Top-k policy chunks + scores
    API->>AOI: Generate answer (GPT-4o, chunks as context)
    AOI-->>API: Answer + citations + confidence
    API->>API: Validate citations, append disclaimer
    API->>R: Store conversation context
    API->>PG: Log message + analytics event
    API->>BS: Response activity
    BS->>T: Formatted response
    T->>E: Answer with citations + disclaimer
```

### Document Ingestion Flow

```mermaid
sequenceDiagram
    participant A as Admin
    participant API as Chatbot API
    participant BLOB as Azure Blob Storage
    participant Q as Redis (Celery Queue)
    participant W as Celery Worker
    participant AOI as Azure OpenAI
    participant AIS as Azure AI Search
    participant PG as PostgreSQL

    A->>API: POST /api/admin/documents (upload PDF)
    API->>BLOB: Store raw document
    API->>PG: Create document metadata record
    API->>Q: Enqueue ingest_document task
    Q->>W: Pick up task
    W->>BLOB: Download raw document
    W->>W: Extract text (preserve structure)
    W->>W: Chunk into semantic sections
    W->>AOI: Generate embeddings (text-embedding-3-large)
    AOI-->>W: Embedding vectors
    W->>AIS: Upsert chunks + vectors into index
    W->>PG: Update document status = indexed
    W->>API: Task complete notification
```

### Escalation Flow

```mermaid
sequenceDiagram
    participant E as Employee
    participant API as Chatbot API
    participant SN as ServiceNow
    participant AGENT as Live Agent

    E->>API: "Talk to a person"
    API->>API: Detect escalation intent
    API->>API: Compile conversation transcript
    API->>SN: POST /api/interaction (transcript + intent)
    SN-->>API: Incident ID
    API->>E: "Connecting you with support (ref: INC-12345)"
    SN->>AGENT: Route incident with transcript
    AGENT->>E: Live conversation begins
```

---

## Infrastructure Summary

| Component | Azure Service | SKU / Tier | ADR |
|-----------|---------------|------------|-----|
| Chat API + Admin API | Azure Container Apps | Consumption (autoscale 2–10) | ADR-0008 |
| Celery Workers | Azure Container Apps | Consumption (autoscale 1–5) | ADR-0008 |
| LLM (completions) | Azure OpenAI Service | GPT-4o deployment | ADR-0010 |
| LLM (classification) | Azure OpenAI Service | GPT-4o-mini deployment | ADR-0010 |
| Embeddings | Azure OpenAI Service | text-embedding-3-large | ADR-0010 |
| Vector + keyword search | Azure AI Search | Standard S1 | ADR-0009 |
| Relational database | Azure Database for PostgreSQL | Flexible Server, General Purpose | ADR-0009 |
| Cache + message broker | Azure Cache for Redis | Standard C1 | ADR-0009 |
| Document storage | Azure Blob Storage | Standard LRS | ADR-0009 |
| Bot routing | Azure Bot Service | Standard | ADR-0011 |
| Identity | Microsoft Entra ID | — (existing tenant) | ADR-0011 |
| Secrets | Azure Key Vault | Standard | — |
| Container registry | Azure Container Registry | Basic | — |
| Observability | Azure Monitor + Application Insights | — | — |

---

## Security Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                    Internet                                  │
│  ┌──────────┐  ┌──────────────┐                             │
│  │ MS Teams │  │ Intranet     │                             │
│  └─────┬────┘  └──────┬───────┘                             │
│        │               │                                     │
├────────┼───────────────┼─────────────────────────────────────┤
│        ▼               ▼         Azure Boundary              │
│  ┌─────────────────────────┐                                 │
│  │  Azure Bot Service      │  (TLS 1.2+, Entra ID auth)    │
│  │  (no public API direct) │                                 │
│  └────────────┬────────────┘                                 │
│               ▼                                              │
│  ┌─────────────────────────┐                                 │
│  │  ACA VNet (internal)    │                                 │
│  │  ┌──────────────────┐   │                                 │
│  │  │ Chatbot API      │   │  Managed Identity auth to:     │
│  │  │ Celery Workers   │   │  - Azure OpenAI                │
│  │  └──────────────────┘   │  - AI Search                   │
│  │                         │  - PostgreSQL                   │
│  │  All data services:     │  - Redis                       │
│  │  private endpoints      │  - Blob Storage                │
│  │  within VNet            │  - Key Vault                   │
│  └─────────────────────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

- No direct public access to the API — all employee traffic routes through Azure
  Bot Service
- Admin console access via Entra ID-authenticated API endpoints on ACA ingress
  (restricted to corporate network / VPN)
- All Azure service connections use managed identity — no credentials in config
- All data services use private endpoints within the ACA VNet
- Conversation logs encrypted at rest (AES-256) and auto-purged after 90 days
