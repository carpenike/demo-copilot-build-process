# Data Model: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-16
> **Produced by:** Design Agent
> **Related ADRs:** ADR-0009 (data storage), ADR-0010 (RAG architecture)

---

## 1. Entity Relationship Diagram

```mermaid
erDiagram
    DOCUMENT ||--o{ DOCUMENT_VERSION : "has versions"
    DOCUMENT ||--o{ DOCUMENT_CHUNK : "is chunked into"
    DOCUMENT }o--|| POLICY_CATEGORY : "belongs to"
    DOCUMENT_VERSION ||--o{ DOCUMENT_CHUNK : "produces chunks"

    CONVERSATION ||--o{ MESSAGE : "contains"
    CONVERSATION }o--|| USER_SESSION : "belongs to"

    MESSAGE ||--o| FEEDBACK : "may have"
    MESSAGE ||--o{ CITATION : "may reference"

    ESCALATION }o--|| CONVERSATION : "created from"

    FEEDBACK_FLAG }o--|| FEEDBACK : "aggregates"

    ANALYTICS_EVENT }o--|| CONVERSATION : "tracked from"

    DOCUMENT {
        uuid id PK
        string title
        string document_external_id
        uuid category_id FK
        string source_type "sharepoint | wordpress | blob"
        string source_url
        date effective_date
        date review_date
        string owner
        string status "active | retired"
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENT_VERSION {
        uuid id PK
        uuid document_id FK
        integer version_number
        string blob_path "path in Azure Blob Storage"
        string file_type "pdf | docx | html"
        integer page_count
        string indexed_by "admin user_id"
        string indexing_status "pending | processing | completed | failed"
        timestamp indexed_at
        timestamp created_at
    }

    DOCUMENT_CHUNK {
        uuid id PK
        uuid document_id FK
        uuid version_id FK
        integer chunk_index
        string section_heading
        text content
        string ai_search_doc_id "ID in Azure AI Search index"
        integer token_count
        timestamp created_at
    }

    POLICY_CATEGORY {
        uuid id PK
        string name "HR | IT | Finance | Facilities | Legal | Compliance | Safety"
        string description
        integer document_count "denormalized for coverage report"
        timestamp last_updated
    }

    CONVERSATION {
        uuid id PK
        string user_id "from Entra ID JWT"
        string channel "teams | web"
        string status "active | escalated | closed"
        timestamp started_at
        timestamp last_activity_at
        timestamp expires_at "90-day TTL per NFR-008"
    }

    MESSAGE {
        uuid id PK
        uuid conversation_id FK
        string role "user | assistant | system"
        text content
        jsonb metadata "intent, confidence, checklist items, etc."
        timestamp created_at
    }

    CITATION {
        uuid id PK
        uuid message_id FK
        uuid document_id FK
        string section_heading
        date effective_date
        string source_url
    }

    FEEDBACK {
        uuid id PK
        uuid message_id FK
        string user_id
        string rating "positive | negative"
        text comment "optional free-text"
        timestamp created_at
    }

    FEEDBACK_FLAG {
        uuid id PK
        string topic "derived from intent classification"
        integer negative_count
        string status "flagged | reviewed | resolved"
        timestamp first_flagged_at
        timestamp reviewed_at
    }

    ESCALATION {
        uuid id PK
        uuid conversation_id FK
        string user_id
        string target_team "HR | IT | Facilities"
        string servicenow_ticket_id "created via ServiceNow API"
        text transcript_summary
        string identified_intent
        timestamp created_at
    }

    USER_SESSION {
        string user_id PK "from Entra ID JWT"
        string display_name
        string department
        string location
        string role "Employee | Administrator"
        timestamp last_active_at
    }

    ANALYTICS_EVENT {
        uuid id PK
        uuid conversation_id FK
        string event_type "query | answer | escalation | feedback | fallback"
        string intent
        string policy_domain
        boolean resolved "answered without escalation"
        float confidence_score
        integer response_time_ms
        timestamp created_at
    }
```

---

## 2. Storage Distribution

| Entity | Primary Store | Secondary Store | Rationale |
|--------|--------------|-----------------|-----------|
| `DOCUMENT` | PostgreSQL | — | Relational metadata with versioning |
| `DOCUMENT_VERSION` | PostgreSQL | Azure Blob Storage (raw files) | Metadata in PG, raw files in Blob |
| `DOCUMENT_CHUNK` | PostgreSQL (metadata) | Azure AI Search (content + embeddings) | Chunks indexed for vector search; metadata tracked in PG for lineage |
| `POLICY_CATEGORY` | PostgreSQL | — | Reference data for coverage report (FR-033) |
| `CONVERSATION` | PostgreSQL | Azure Cache for Redis (active session context) | PG for persistence; Redis for fast session lookup (FR-009) |
| `MESSAGE` | PostgreSQL | Redis (recent messages in active session) | PG for history; Redis for conversation context window |
| `CITATION` | PostgreSQL | — | Linked to messages for audit trail |
| `FEEDBACK` | PostgreSQL | — | Persisted for analytics (FR-028, FR-030) |
| `FEEDBACK_FLAG` | PostgreSQL | — | Aggregation for admin review (FR-030) |
| `ESCALATION` | PostgreSQL | — | Audit trail for ServiceNow handoffs |
| `USER_SESSION` | Azure Cache for Redis | — | Cached profile data from Graph API, 24h TTL |
| `ANALYTICS_EVENT` | PostgreSQL | — | Source data for analytics dashboard (FR-029) |

---

## 3. Azure AI Search Index Schema

The AI Search index stores the searchable representation of document chunks.
This is separate from the PostgreSQL metadata.

**Index name:** `policy-chunks-v1`

| Field | Type | Searchable | Filterable | Sortable | Facetable | Retrievable |
|-------|------|-----------|------------|----------|-----------|-------------|
| `id` | `Edm.String` (key) | — | — | — | — | ✅ |
| `document_id` | `Edm.String` | — | ✅ | — | — | ✅ |
| `version_id` | `Edm.String` | — | ✅ | — | — | ✅ |
| `chunk_index` | `Edm.Int32` | — | — | ✅ | — | ✅ |
| `content` | `Edm.String` | ✅ (BM25) | — | — | — | ✅ |
| `section_heading` | `Edm.String` | ✅ | ✅ | — | — | ✅ |
| `document_title` | `Edm.String` | ✅ | ✅ | — | ✅ | ✅ |
| `category` | `Edm.String` | — | ✅ | — | ✅ | ✅ |
| `effective_date` | `Edm.DateTimeOffset` | — | ✅ | ✅ | — | ✅ |
| `source_url` | `Edm.String` | — | — | — | — | ✅ |
| `owner` | `Edm.String` | — | ✅ | — | — | ✅ |
| `content_vector` | `Collection(Edm.Single)` | vector (1536d, cosine) | — | — | — | — |

**Vector search configuration:**
- Algorithm: HNSW
- Dimensions: 1536 (text-embedding-3-large)
- Metric: cosine
- Semantic configuration: enabled with semantic ranker

---

## 4. Redis Data Structures

| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `session:{user_id}` | Hash | 24h | Cached user profile (name, dept, location, role) |
| `conv:{conversation_id}` | List | 90 days | Recent message history for conversation context window |
| `conv:{conversation_id}:meta` | Hash | 90 days | Conversation metadata (status, channel, identified intent) |
| `rate:{user_id}` | String (counter) | 1 min | Token bucket rate limiter per user |
| `cache:query:{hash}` | String (JSON) | 1 hour | Response cache for identical queries |

---

## 5. Data Retention & Lifecycle

| Data | Retention | Mechanism | Requirement |
|------|-----------|-----------|-------------|
| Conversation logs (messages) | 90 days | PostgreSQL scheduled deletion job | NFR-008 |
| Conversation context (Redis) | 90 days | Redis TTL auto-expiry | NFR-008 |
| Feedback records | 90 days (raw), permanent (aggregated) | PG job aggregates then deletes raw | NFR-008 |
| Analytics events | Permanent (anonymized after 90 days) | PG job strips user_id after 90 days | NFR-008, FR-029 |
| Document metadata | Permanent | — | FR-006 (version history) |
| Document chunks | Active version retained; old versions removed from AI Search | Ingestion worker manages lifecycle | FR-006 |
| Raw document files (Blob) | Permanent (audit trail) | — | FR-006 |
| User session cache (Redis) | 24 hours | Redis TTL auto-expiry | Performance optimization |

---

## 6. Data Flow Diagram

```mermaid
flowchart TD
    subgraph Sources ["Document Sources"]
        SP[SharePoint Online]
        WP[WordPress CMS]
        BS[Azure Blob Storage<br/>uploaded via Admin Console]
    end

    subgraph Ingestion ["Ingestion Pipeline (Celery Worker)"]
        EXT[Text Extraction<br/>PDF / DOCX / HTML]
        CHK[Semantic Chunking<br/>heading-aware splitting]
        EMB[Embedding Generation<br/>Azure OpenAI<br/>text-embedding-3-large]
        IDX[Index Upload<br/>Azure AI Search]
        META[Metadata Storage<br/>PostgreSQL]
    end

    subgraph Query ["Query Pipeline (Chat API)"]
        QRY[User Query]
        INT[Intent Classification]
        QEMB[Query Embedding<br/>Azure OpenAI]
        HYB[Hybrid Search<br/>Azure AI Search<br/>vector + BM25]
        RANK[Semantic Re-ranking]
        PROMPT[Prompt Assembly]
        LLM[Azure OpenAI GPT-4o<br/>Chat Completion]
        PARSE[Response Parser<br/>answer + citations + checklist]
    end

    SP --> EXT
    WP --> EXT
    BS --> EXT
    EXT --> CHK --> EMB --> IDX
    EXT --> META

    QRY --> INT --> QEMB --> HYB --> RANK --> PROMPT --> LLM --> PARSE
```
