# Wireframe Spec: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-16
> **Produced by:** Design Agent
> **Input:** `projects/policy-chatbot/requirements/requirements.md`
> **Related ADRs:** ADR-0007, ADR-0008, ADR-0009, ADR-0010, ADR-0011

---

## API Endpoints

### Authentication

**Mechanism:** OAuth 2.0 / OpenID Connect via Microsoft Entra ID (ADR-0011)

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <entra_id_access_token>` |

Error responses:
- `401 Unauthorized` — missing or invalid token
- `403 Forbidden` — valid token but insufficient App Role (e.g., employee hitting admin endpoint)

---

### Health & Readiness

#### `GET /health`

**Purpose:** Liveness probe — confirms the process is running.
**Auth required:** No
**Related:** Enterprise security policy

**Response `200 OK`:**
```json
{
  "status": "healthy"
}
```

---

#### `GET /ready`

**Purpose:** Readiness probe — confirms all dependencies are reachable (PostgreSQL, Redis, Azure AI Search, Azure OpenAI).
**Auth required:** No
**Related:** Enterprise security policy

**Response `200 OK`:**
```json
{
  "status": "ready",
  "checks": {
    "postgresql": "ok",
    "redis": "ok",
    "ai_search": "ok",
    "azure_openai": "ok"
  }
}
```

**Response `503 Service Unavailable`:**
```json
{
  "status": "not_ready",
  "checks": {
    "postgresql": "ok",
    "redis": "ok",
    "ai_search": "ok",
    "azure_openai": "unavailable"
  }
}
```

---

### Chat API

#### `POST /v1/chat/conversations`

**Purpose:** Start a new conversation session.
**Auth required:** Yes (Employee or Administrator role)
**Related requirements:** FR-007, FR-009, FR-011

**Request body:**
```json
{
  "channel": "web | teams"
}
```

**Response `201 Created`:**
```json
{
  "conversation_id": "uuid",
  "greeting": "Hi Alex! I'm the Policy Assistant. How can I help you today?",
  "user_context": {
    "display_name": "Alex Johnson",
    "department": "Engineering",
    "location": "HQ - Building A"
  },
  "created_at": "2026-03-16T10:00:00Z"
}
```

---

#### `POST /v1/chat/conversations/{conversation_id}/messages`

**Purpose:** Send a message in an existing conversation and receive the chatbot's response.
**Auth required:** Yes (Employee or Administrator role)
**Related requirements:** FR-007, FR-008, FR-009, FR-012–FR-021

**Request body:**
```json
{
  "content": "How do I request parental leave?"
}
```

**Response `200 OK` — Factual answer with citation:**
```json
{
  "message_id": "uuid",
  "role": "assistant",
  "content": "Acme's parental leave policy provides up to 16 weeks of paid leave for primary caregivers and 6 weeks for secondary caregivers. Leave begins on the date of birth or adoption placement.",
  "response_type": "answer",
  "citations": [
    {
      "document_title": "Parental Leave Policy",
      "section": "§3.1 Leave Duration",
      "effective_date": "2025-07-01",
      "source_url": "https://sharepoint.acme.com/policies/hr/parental-leave"
    }
  ],
  "disclaimer": "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version.",
  "feedback_enabled": true,
  "created_at": "2026-03-16T10:00:05Z"
}
```

**Response `200 OK` — Procedural answer with checklist:**
```json
{
  "message_id": "uuid",
  "role": "assistant",
  "content": "Here's what you need to do to request parental leave:",
  "response_type": "checklist",
  "checklist": [
    {
      "step": 1,
      "description": "Notify your manager at least 30 days before your expected leave start date",
      "type": "manual",
      "detail": "Have a conversation with your direct manager about your leave dates and coverage plan."
    },
    {
      "step": 2,
      "description": "Submit the Parental Leave Request form in Workday",
      "type": "assisted",
      "action": {
        "kind": "form_link",
        "label": "Open Parental Leave Request in Workday",
        "url": "https://workday.acme.com/leave/request?type=parental"
      }
    },
    {
      "step": 3,
      "description": "Contact the Benefits team to discuss benefits continuation during leave",
      "type": "assisted",
      "action": {
        "kind": "contact",
        "name": "Benefits Team",
        "email": "benefits@acme.com",
        "phone": "+1-555-0199",
        "office": "HQ Building A, Room 302"
      }
    },
    {
      "step": 4,
      "description": "Schedule a return-to-work meeting with your manager for your last week of leave",
      "type": "assisted",
      "action": {
        "kind": "scheduling",
        "label": "Create calendar invite",
        "url": "https://outlook.office.com/calendar/new"
      }
    }
  ],
  "citations": [
    {
      "document_title": "Parental Leave Policy",
      "section": "§5 Request Procedure",
      "effective_date": "2025-07-01",
      "source_url": "https://sharepoint.acme.com/policies/hr/parental-leave"
    }
  ],
  "disclaimer": "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version.",
  "feedback_enabled": true,
  "created_at": "2026-03-16T10:00:05Z"
}
```

**Response `200 OK` — No relevant policy found:**
```json
{
  "message_id": "uuid",
  "role": "assistant",
  "content": "I wasn't able to find a policy covering that topic. Would you like me to connect you with HR support?",
  "response_type": "no_match",
  "escalation_offered": true,
  "disclaimer": "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version.",
  "feedback_enabled": true,
  "created_at": "2026-03-16T10:00:03Z"
}
```

**Response `200 OK` — Confidential topic detected:**
```json
{
  "message_id": "uuid",
  "role": "assistant",
  "content": "It sounds like your question may involve a sensitive HR matter. I want to make sure you get the right support. Would you like me to connect you directly with an HR representative who can help confidentially?",
  "response_type": "confidential_escalation",
  "escalation_offered": true,
  "feedback_enabled": false,
  "created_at": "2026-03-16T10:00:02Z"
}
```

**Response `200 OK` — LLM fallback mode:**
```json
{
  "message_id": "uuid",
  "role": "assistant",
  "content": "I found some potentially relevant policy documents, but I'm currently operating in basic search mode. Here are the top results:",
  "response_type": "fallback_search",
  "search_results": [
    {
      "document_title": "Parental Leave Policy",
      "section": "§3.1 Leave Duration",
      "snippet": "Primary caregivers are eligible for up to 16 weeks of paid leave...",
      "source_url": "https://sharepoint.acme.com/policies/hr/parental-leave"
    }
  ],
  "fallback_notice": "This is a basic search result, not a full answer. Try again later for a complete answer, or I can connect you with a support agent.",
  "escalation_offered": true,
  "created_at": "2026-03-16T10:00:03Z"
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Empty or invalid message content |
| `401` | Unauthenticated |
| `403` | Insufficient permissions |
| `404` | Conversation not found or belongs to another user |
| `429` | Rate limited |

---

#### `POST /v1/chat/conversations/{conversation_id}/escalate`

**Purpose:** Escalate the current conversation to a live service desk agent.
**Auth required:** Yes (Employee or Administrator role)
**Related requirements:** FR-025, FR-026

**Request body:**
```json
{
  "target_team": "hr | it | facilities"
}
```

**Response `201 Created`:**
```json
{
  "escalation_id": "uuid",
  "servicenow_ticket_id": "INC0012345",
  "message": "I've connected you with the HR support team. A representative will follow up shortly. Your conversation history has been shared so you don't need to repeat yourself.",
  "created_at": "2026-03-16T10:01:00Z"
}
```

---

#### `POST /v1/chat/conversations/{conversation_id}/messages/{message_id}/feedback`

**Purpose:** Submit feedback on a chatbot response.
**Auth required:** Yes (Employee or Administrator role)
**Related requirements:** FR-028

**Request body:**
```json
{
  "rating": "positive | negative",
  "comment": "This was very helpful, thank you!"
}
```

**Response `201 Created`:**
```json
{
  "feedback_id": "uuid",
  "created_at": "2026-03-16T10:00:10Z"
}
```

---

### Admin API

#### `GET /v1/admin/documents`

**Purpose:** List all policy documents with metadata and indexing status.
**Auth required:** Yes (Administrator role only)
**Related requirements:** FR-031, FR-033

**Request:**
```
Query params:
  category: string (optional) — filter by policy domain
  status: string (optional) — "active" | "retired"
  cursor: string (optional) — pagination cursor
  limit: integer (optional, default 20, max 100)
```

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "uuid",
      "title": "Parental Leave Policy",
      "document_external_id": "HR-POL-042",
      "category": "HR",
      "source_type": "sharepoint",
      "source_url": "https://sharepoint.acme.com/policies/hr/parental-leave",
      "effective_date": "2025-07-01",
      "review_date": "2026-07-01",
      "owner": "VP Human Resources",
      "status": "active",
      "current_version": 3,
      "last_indexed_at": "2026-03-15T14:30:00Z",
      "indexing_status": "completed"
    }
  ],
  "next_cursor": "string | null",
  "total": 140
}
```

---

#### `POST /v1/admin/documents`

**Purpose:** Upload a new policy document and store it in Blob Storage.
**Auth required:** Yes (Administrator role only)
**Related requirements:** FR-031

**Request:** `multipart/form-data`
```
Fields:
  file: binary (required) — PDF or DOCX file
  title: string (required, max 255 chars)
  document_external_id: string (required) — e.g., "HR-POL-042"
  category: string (required) — "HR" | "IT" | "Finance" | "Facilities" | "Legal" | "Compliance" | "Safety"
  effective_date: date (required) — ISO 8601
  review_date: date (optional)
  owner: string (required)
```

**Response `201 Created`:**
```json
{
  "id": "uuid",
  "title": "Parental Leave Policy",
  "document_external_id": "HR-POL-042",
  "category": "HR",
  "status": "active",
  "version": 1,
  "indexing_status": "pending",
  "created_at": "2026-03-16T10:00:00Z"
}
```

---

#### `POST /v1/admin/documents/{document_id}/reindex`

**Purpose:** Trigger re-indexing of a specific document.
**Auth required:** Yes (Administrator role only)
**Related requirements:** FR-005

**Response `202 Accepted`:**
```json
{
  "task_id": "uuid",
  "document_id": "uuid",
  "status": "processing",
  "message": "Re-indexing started. Check status via GET /v1/admin/documents/{document_id}."
}
```

---

#### `POST /v1/admin/documents/reindex-all`

**Purpose:** Trigger full corpus re-indexing.
**Auth required:** Yes (Administrator role only)
**Related requirements:** FR-005

**Response `202 Accepted`:**
```json
{
  "task_id": "uuid",
  "status": "processing",
  "document_count": 140,
  "message": "Full corpus re-indexing started. Estimated completion: ~2 hours."
}
```

---

#### `PATCH /v1/admin/documents/{document_id}`

**Purpose:** Update document metadata or retire a document.
**Auth required:** Yes (Administrator role only)
**Related requirements:** FR-031

**Request body:**
```json
{
  "status": "retired"
}
```

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "title": "Old Travel Policy",
  "status": "retired",
  "updated_at": "2026-03-16T10:00:00Z"
}
```

---

#### `GET /v1/admin/documents/{document_id}/versions`

**Purpose:** View version history for a document.
**Auth required:** Yes (Administrator role only)
**Related requirements:** FR-006

**Response `200 OK`:**
```json
{
  "data": [
    {
      "version_id": "uuid",
      "version_number": 3,
      "file_type": "pdf",
      "page_count": 12,
      "indexed_by": "admin@acme.com",
      "indexing_status": "completed",
      "indexed_at": "2026-03-15T14:30:00Z",
      "created_at": "2026-03-15T14:25:00Z"
    }
  ]
}
```

---

#### `POST /v1/admin/test-query`

**Purpose:** Preview how the chatbot would answer a question (against current or pending corpus).
**Auth required:** Yes (Administrator role only)
**Related requirements:** FR-032

**Request body:**
```json
{
  "query": "How do I request parental leave?",
  "include_pending_documents": true
}
```

**Response `200 OK`:**
```json
{
  "current_corpus_response": {
    "content": "...",
    "citations": [...]
  },
  "pending_corpus_response": {
    "content": "...",
    "citations": [...]
  }
}
```

---

#### `GET /v1/admin/analytics`

**Purpose:** Retrieve analytics data for the admin dashboard.
**Auth required:** Yes (Administrator role only)
**Related requirements:** FR-029

**Request:**
```
Query params:
  period: string (required) — "day" | "week" | "month"
  start_date: date (optional) — ISO 8601
  end_date: date (optional) — ISO 8601
```

**Response `200 OK`:**
```json
{
  "period": "week",
  "start_date": "2026-03-09",
  "end_date": "2026-03-16",
  "query_volume": 2340,
  "resolution_rate": 0.78,
  "escalation_rate": 0.12,
  "average_satisfaction": 4.2,
  "top_intents": [
    {"intent": "parental_leave", "count": 156},
    {"intent": "pto_balance", "count": 134},
    {"intent": "parking_badge", "count": 98}
  ],
  "unanswered_queries": [
    {
      "query": "What's the policy on pet-friendly offices?",
      "count": 7,
      "last_asked": "2026-03-15T16:30:00Z"
    }
  ]
}
```

---

#### `GET /v1/admin/analytics/flagged-topics`

**Purpose:** View topics flagged for admin review due to repeated negative feedback.
**Auth required:** Yes (Administrator role only)
**Related requirements:** FR-030

**Response `200 OK`:**
```json
{
  "data": [
    {
      "flag_id": "uuid",
      "topic": "bereavement_leave",
      "negative_count": 5,
      "status": "flagged",
      "sample_queries": [
        "What is the bereavement leave policy for extended family?",
        "Does bereavement apply to in-laws?"
      ],
      "sample_comments": [
        "The answer didn't cover in-laws",
        "Missing information about extended family"
      ],
      "first_flagged_at": "2026-03-10T09:00:00Z"
    }
  ]
}
```

---

#### `GET /v1/admin/coverage`

**Purpose:** Display policy coverage report by domain.
**Auth required:** Yes (Administrator role only)
**Related requirements:** FR-033

**Response `200 OK`:**
```json
{
  "domains": [
    {"name": "HR", "document_count": 42, "last_updated": "2026-03-15"},
    {"name": "IT", "document_count": 28, "last_updated": "2026-03-10"},
    {"name": "Finance", "document_count": 18, "last_updated": "2026-02-28"},
    {"name": "Facilities", "document_count": 22, "last_updated": "2026-03-12"},
    {"name": "Legal", "document_count": 15, "last_updated": "2026-03-01"},
    {"name": "Compliance", "document_count": 12, "last_updated": "2026-02-15"},
    {"name": "Safety", "document_count": 3, "last_updated": "2026-01-20"}
  ],
  "total_documents": 140,
  "gaps": []
}
```

---

## UI Screen Inventory

### Employee-Facing Screens

#### Screen 1: Web Chat Widget

**Purpose:** Embedded chat interface on the corporate intranet for policy Q&A.
**Related requirements:** FR-007, FR-009, FR-011, FR-012–FR-021, FR-025, FR-028

**Key components:**
- **Chat header** — "Policy Assistant" branding, minimize/close buttons
- **Message list** — scrollable conversation history
  - User messages (right-aligned)
  - Assistant messages (left-aligned) with:
    - Answer text
    - Citation block (collapsible, shows document title, section, date, link)
    - Checklist (numbered steps with Assisted/Manual badges and action buttons)
    - Disclaimer footer (small text, every response)
  - Fallback search results (distinct styling, "basic search result" label)
  - Escalation messages
- **Feedback buttons** — thumbs up/down on each assistant message, optional comment modal
- **Input area** — text input field, send button, "Talk to a person" link
- **Typing indicator** — shown while waiting for response

**Accessibility:** WCAG 2.1 AA, keyboard navigation, screen reader labels on all interactive elements (NFR-017, NFR-018)

---

### Admin-Facing Screens

#### Screen 2: Admin Dashboard

**Purpose:** Landing page for policy administrators showing key metrics.
**Related requirements:** FR-029, FR-030

**Key components:**
- **Summary cards** — query volume (today/week/month), resolution rate, escalation rate, satisfaction score
- **Top intents chart** — bar chart of top 20 intents by frequency
- **Flagged topics table** — topics with 3+ negative feedback, with status and action buttons
- **Unanswered queries log** — filterable/searchable table of queries that received no match
- **Date range picker** — filter all metrics by time period

---

#### Screen 3: Document Management

**Purpose:** Upload, view, re-index, and retire policy documents.
**Related requirements:** FR-031, FR-005, FR-006

**Key components:**
- **Document table** — title, category, status, version, last indexed, indexing status
  - Row actions: view versions, re-index, retire
  - Filterable by category, status
  - Cursor-based pagination
- **Upload form** — file picker (PDF/DOCX), title, external ID, category dropdown, effective date, owner
- **Bulk actions** — "Re-index All" button (triggers full corpus re-indexing)
- **Version history modal** — shows all versions of a selected document with dates and indexing status

---

#### Screen 4: Test Query Tool

**Purpose:** Preview chatbot answers before/after document changes.
**Related requirements:** FR-032

**Key components:**
- **Query input** — text field for test question
- **Toggle** — "Include pending documents" checkbox
- **Results pane** — side-by-side comparison showing:
  - Current corpus response (answer, citations, checklist)
  - Pending corpus response (if toggle is on)

---

#### Screen 5: Policy Coverage Report

**Purpose:** Show which policy domains have indexed content and gaps.
**Related requirements:** FR-033

**Key components:**
- **Domain cards** — one per policy domain (HR, IT, Finance, Facilities, Legal, Compliance, Safety)
  - Document count, last updated date
  - Visual indicator: green (covered), red (zero documents = gap)
- **Total document count** — aggregate across all domains

---

## Error Response Format

All API error responses follow RFC 7807 Problem Details format:

```json
{
  "type": "https://api.acme.com/problems/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "The 'category' field must be one of: HR, IT, Finance, Facilities, Legal, Compliance, Safety.",
  "instance": "/v1/admin/documents"
}
```

---

## Rate Limiting

| Endpoint Group | Limit | Window |
|----------------|-------|--------|
| Chat messages | 30 requests | per minute per user |
| Admin endpoints | 60 requests | per minute per user |
| Document upload | 10 requests | per hour per user |
| Full re-index | 1 request | per hour (global) |
