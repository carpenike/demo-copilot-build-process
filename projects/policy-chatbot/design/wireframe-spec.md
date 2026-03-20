# Wireframe Spec: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-20
> **Produced by:** Design Agent
> **Input:** `projects/policy-chatbot/requirements/requirements.md`
> **Related ADRs:** ADR-0007, ADR-0008, ADR-0009, ADR-0010, ADR-0011, ADR-0012

---

## API Endpoints

### Authentication

**Mechanism:** OAuth 2.0 Bearer Token (Microsoft Entra ID) — see ADR-0012

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <entra_id_jwt>` |

All endpoints except `/health` and `/ready` require a valid bearer token.

Standard error responses for auth failures:
- `401 Unauthorized` — missing or invalid token
- `403 Forbidden` — valid token but insufficient role (e.g., employee calling admin endpoint)

### Common Error Format (RFC 7807)

All error responses use Problem Details format:

```json
{
  "type": "https://policy-chatbot.acme.com/errors/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "Field 'category' must be one of: HR, IT, Finance, Facilities, Legal, Compliance, Safety",
  "instance": "/v1/admin/documents"
}
```

---

## Health & Readiness

### Endpoint: `GET /health`

**Purpose:** Liveness probe — confirms the process is running
**Auth required:** No

**Response `200 OK`:**
```json
{
  "status": "healthy"
}
```

---

### Endpoint: `GET /ready`

**Purpose:** Readiness probe — confirms all dependencies are reachable
**Auth required:** No

**Response `200 OK`:**
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "search": "ok",
    "openai": "ok"
  }
}
```

**Response `503 Service Unavailable`:**
```json
{
  "status": "not_ready",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "search": "timeout",
    "openai": "ok"
  }
}
```

---

## Chat API

### Endpoint: `POST /v1/chat`

**Purpose:** Send a message and receive a policy-grounded response (FR-007, FR-008, FR-009, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017)
**Auth required:** Yes
**Required role:** Employee or Admin

**Request body:**
```json
{
  "conversation_id": "uuid (optional — omit to start a new conversation)",
  "message": "string (required, max 2000 chars)"
}
```

**Response `200 OK` — Standard answer:**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "response": {
    "type": "answer",
    "content": "Bereavement leave provides up to 5 days of paid leave for the death of an immediate family member...",
    "citations": [
      {
        "document_title": "HR-POL-042: Bereavement Leave Policy",
        "section": "Section 3.1 — Eligibility and Duration",
        "effective_date": "2025-09-01",
        "source_url": "https://intranet.acme.com/policies/HR-POL-042"
      }
    ],
    "disclaimer": "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version.",
    "intent": {
      "type": "factual",
      "domain": "HR",
      "confidence": 0.94
    }
  }
}
```

**Response `200 OK` — Procedural answer with checklist (FR-017, FR-018, FR-019, FR-020):**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "response": {
    "type": "checklist",
    "content": "Here are the steps to request FMLA leave:",
    "checklist": [
      {
        "step": 1,
        "description": "Notify your manager of your need for FMLA leave",
        "action_type": "manual",
        "details": "Contact your direct manager verbally or via email at least 30 days before the leave start date when foreseeable"
      },
      {
        "step": 2,
        "description": "Submit the FMLA request form in Workday",
        "action_type": "assisted",
        "assistance": {
          "type": "form_link",
          "label": "Open FMLA Request Form",
          "url": "https://workday.acme.com/fmla-request"
        }
      },
      {
        "step": 3,
        "description": "Obtain a medical certification from your healthcare provider",
        "action_type": "manual",
        "details": "Call your healthcare provider to request a medical certification. The form must be returned to HR within 15 calendar days."
      },
      {
        "step": 4,
        "description": "Submit the medical certification to HR Benefits",
        "action_type": "assisted",
        "assistance": {
          "type": "contact",
          "label": "HR Benefits Team",
          "email": "benefits@acme.com",
          "phone": "+1-555-0142",
          "location": "Building A, Room 105"
        }
      }
    ],
    "citations": [
      {
        "document_title": "HR-POL-018: FMLA Leave Policy",
        "section": "Section 5 — Request Procedure",
        "effective_date": "2025-06-15",
        "source_url": "https://intranet.acme.com/policies/HR-POL-018"
      }
    ],
    "disclaimer": "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version.",
    "intent": {
      "type": "procedural",
      "domain": "HR",
      "confidence": 0.91
    }
  }
}
```

**Response `200 OK` — Wayfinding assistance (FR-022, FR-023, FR-024):**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "response": {
    "type": "answer",
    "content": "The HR office is located in Building C, 2nd Floor, Room 204.",
    "wayfinding": {
      "available": true,
      "building": "Building C",
      "floor": "2nd Floor",
      "room": "Room 204",
      "campus_map_url": "https://maps.acme.com/hq?dest=C-204"
    },
    "citations": [],
    "disclaimer": "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version.",
    "intent": {
      "type": "wayfinding",
      "domain": "Facilities",
      "confidence": 0.88
    }
  }
}
```

**Response `200 OK` — No matching policy (FR-014):**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "response": {
    "type": "no_match",
    "content": "I couldn't find a matching policy for your question. Would you like me to connect you with the appropriate support team?",
    "suggested_escalation": {
      "team": "HR Service Desk",
      "channel": "servicenow"
    },
    "citations": [],
    "disclaimer": "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version.",
    "intent": {
      "type": "unknown",
      "domain": null,
      "confidence": 0.23
    }
  }
}
```

**Response `200 OK` — Confidential topic detected (FR-016):**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "response": {
    "type": "confidential_escalation",
    "content": "This appears to be a sensitive matter that requires confidential support. I'm connecting you directly with HR rather than providing an automated response.",
    "escalation": {
      "team": "HR Confidential Support",
      "phone": "+1-555-0199",
      "email": "confidential-hr@acme.com",
      "note": "All communications are handled confidentially."
    },
    "citations": [],
    "disclaimer": "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version."
  }
}
```

**Response `200 OK` — Automatic escalation offer (FR-027):**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "response": {
    "type": "escalation_offer",
    "content": "I'm having trouble finding the right answer. Would you like me to connect you with someone who can help?",
    "suggested_escalation": {
      "team": "HR Service Desk",
      "channel": "servicenow"
    },
    "citations": [],
    "disclaimer": "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version."
  }
}
```

**Response `200 OK` — LLM fallback (NFR-006):**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "response": {
    "type": "fallback_search",
    "content": "The AI assistant is temporarily unavailable. Here are basic search results that may help:",
    "search_results": [
      {
        "document_title": "HR-POL-042: Bereavement Leave Policy",
        "section": "Section 3.1 — Eligibility",
        "snippet": "Employees are eligible for up to 5 days of paid bereavement leave...",
        "source_url": "https://intranet.acme.com/policies/HR-POL-042"
      }
    ],
    "citations": [],
    "disclaimer": "This is a basic search result, not a full answer. The AI assistant is temporarily unavailable."
  }
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Message is empty or exceeds 2000 chars |
| `401` | Unauthenticated |
| `404` | `conversation_id` not found or does not belong to the user |
| `429` | Rate limit exceeded |
| `503` | All backend services unavailable |

---

### Endpoint: `POST /v1/chat/escalate`

**Purpose:** Initiate a handoff to a live service desk agent (FR-025, FR-026)
**Auth required:** Yes
**Required role:** Employee or Admin

**Request body:**
```json
{
  "conversation_id": "uuid (required)"
}
```

**Response `200 OK`:**
```json
{
  "conversation_id": "uuid",
  "escalation": {
    "status": "initiated",
    "ticket_id": "INC0012345",
    "team": "HR Service Desk",
    "message": "I've created a support ticket and shared our conversation with the service desk. A team member will reach out shortly."
  }
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Missing conversation_id |
| `401` | Unauthenticated |
| `404` | Conversation not found or does not belong to user |
| `502` | ServiceNow API unavailable |

---

## Conversation API

### Endpoint: `GET /v1/conversations`

**Purpose:** List the current user's recent conversations (NFR-010 — users see only their own)
**Auth required:** Yes
**Required role:** Employee or Admin

**Request:**
```
Query params:
  cursor: string (optional) — pagination cursor
  limit: integer (optional, default 20, max 100)
```

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "uuid",
      "started_at": "2026-03-20T10:30:00Z",
      "last_message_at": "2026-03-20T10:35:22Z",
      "message_count": 4,
      "preview": "What is the bereavement leave policy?"
    }
  ],
  "next_cursor": "string | null"
}
```

---

### Endpoint: `GET /v1/conversations/{conversation_id}`

**Purpose:** Retrieve full conversation history for a specific conversation
**Auth required:** Yes
**Required role:** Employee or Admin (own conversations only)

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "started_at": "2026-03-20T10:30:00Z",
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": "What is the bereavement leave policy?",
      "timestamp": "2026-03-20T10:30:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "Bereavement leave provides up to 5 days...",
      "citations": [ ... ],
      "timestamp": "2026-03-20T10:30:03Z"
    }
  ]
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `401` | Unauthenticated |
| `403` | Conversation belongs to another user |
| `404` | Conversation not found |

---

## Feedback API

### Endpoint: `POST /v1/feedback`

**Purpose:** Submit thumbs-up/thumbs-down feedback on a chatbot response (FR-028)
**Auth required:** Yes
**Required role:** Employee or Admin

**Request body:**
```json
{
  "message_id": "uuid (required) — the assistant message being rated",
  "rating": "positive | negative (required)",
  "comment": "string (optional, max 500 chars)"
}
```

**Response `201 Created`:**
```json
{
  "id": "uuid",
  "message_id": "uuid",
  "rating": "negative",
  "comment": "This answer is outdated",
  "created_at": "2026-03-20T10:36:00Z"
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Invalid rating value or missing message_id |
| `401` | Unauthenticated |
| `404` | Message not found |
| `409` | Feedback already submitted for this message |

---

## Admin — Document Management API

### Endpoint: `GET /v1/admin/documents`

**Purpose:** List all documents in the policy corpus with metadata (FR-031)
**Auth required:** Yes
**Required role:** Admin

**Request:**
```
Query params:
  cursor: string (optional) — pagination cursor
  limit: integer (optional, default 20, max 100)
  category: string (optional) — filter by category (HR, IT, Finance, Facilities, Legal, Compliance, Safety)
  status: string (optional) — filter by status (active, retired)
```

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "uuid",
      "title": "HR-POL-042: Bereavement Leave Policy",
      "category": "HR",
      "status": "active",
      "effective_date": "2025-09-01",
      "review_date": "2026-09-01",
      "owner": "Jane Smith",
      "source_url": "https://intranet.acme.com/policies/HR-POL-042",
      "current_version": 3,
      "last_indexed_at": "2026-03-19T14:00:00Z",
      "page_count": 12,
      "created_at": "2024-01-15T09:00:00Z"
    }
  ],
  "next_cursor": "string | null"
}
```

---

### Endpoint: `GET /v1/admin/documents/{document_id}`

**Purpose:** Get detailed information for a specific document, including version history (FR-006)
**Auth required:** Yes
**Required role:** Admin

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "title": "HR-POL-042: Bereavement Leave Policy",
  "category": "HR",
  "status": "active",
  "effective_date": "2025-09-01",
  "review_date": "2026-09-01",
  "owner": "Jane Smith",
  "source_url": "https://intranet.acme.com/policies/HR-POL-042",
  "current_version": 3,
  "last_indexed_at": "2026-03-19T14:00:00Z",
  "page_count": 12,
  "versions": [
    {
      "version": 3,
      "uploaded_at": "2026-03-19T13:55:00Z",
      "uploaded_by": "admin@acme.com",
      "is_active": true,
      "blob_path": "HR/bereavement-leave/v3.pdf"
    },
    {
      "version": 2,
      "uploaded_at": "2025-09-01T10:00:00Z",
      "uploaded_by": "admin@acme.com",
      "is_active": false,
      "blob_path": "HR/bereavement-leave/v2.pdf"
    }
  ]
}
```

---

### Endpoint: `POST /v1/admin/documents`

**Purpose:** Upload a new policy document and trigger indexing (FR-001, FR-031)
**Auth required:** Yes
**Required role:** Admin

**Request:** `multipart/form-data`
```
Fields:
  file: binary (required) — PDF, DOCX, or HTML file (max 50MB)
  title: string (required, max 255 chars)
  category: string (required) — one of: HR, IT, Finance, Facilities, Legal, Compliance, Safety
  effective_date: date (required) — YYYY-MM-DD
  review_date: date (optional) — YYYY-MM-DD
  owner: string (required, max 255 chars)
  source_url: string (optional, max 2048 chars) — URL to the canonical document location
```

**Response `201 Created`:**
```json
{
  "id": "uuid",
  "title": "IT-POL-007: Remote Access Policy",
  "category": "IT",
  "status": "active",
  "effective_date": "2026-03-01",
  "owner": "IT Security Team",
  "version": 1,
  "indexing_status": "in_progress",
  "created_at": "2026-03-20T11:00:00Z"
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Missing required fields, unsupported file type, file too large |
| `401` | Unauthenticated |
| `403` | Not an admin |
| `409` | Document with same title already exists |

---

### Endpoint: `PUT /v1/admin/documents/{document_id}`

**Purpose:** Upload a new version of an existing document (FR-005, FR-006)
**Auth required:** Yes
**Required role:** Admin

**Request:** `multipart/form-data`
```
Fields:
  file: binary (required) — replacement document file
  effective_date: date (optional) — updated effective date
  review_date: date (optional)
  owner: string (optional)
  source_url: string (optional)
```

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "title": "IT-POL-007: Remote Access Policy",
  "version": 2,
  "indexing_status": "in_progress",
  "updated_at": "2026-03-20T11:15:00Z"
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Unsupported file type, file too large |
| `401` | Unauthenticated |
| `403` | Not an admin |
| `404` | Document not found |

---

### Endpoint: `PATCH /v1/admin/documents/{document_id}`

**Purpose:** Update document metadata or retire a document (FR-031)
**Auth required:** Yes
**Required role:** Admin

**Request body:**
```json
{
  "status": "retired (optional — set to retire the document)",
  "title": "string (optional)",
  "category": "string (optional)",
  "effective_date": "date (optional)",
  "review_date": "date (optional)",
  "owner": "string (optional)",
  "source_url": "string (optional)"
}
```

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "title": "HR-POL-042: Bereavement Leave Policy",
  "status": "retired",
  "updated_at": "2026-03-20T11:20:00Z"
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Invalid status value |
| `401` | Unauthenticated |
| `403` | Not an admin |
| `404` | Document not found |

---

### Endpoint: `POST /v1/admin/documents/{document_id}/reindex`

**Purpose:** Trigger re-indexing of a single document (FR-005)
**Auth required:** Yes
**Required role:** Admin

**Request body:** None

**Response `202 Accepted`:**
```json
{
  "document_id": "uuid",
  "indexing_status": "in_progress",
  "estimated_completion": "2026-03-20T11:25:00Z"
}
```

---

### Endpoint: `POST /v1/admin/reindex`

**Purpose:** Trigger full corpus re-indexing (FR-005, NFR-003)
**Auth required:** Yes
**Required role:** Admin

**Request body:** None

**Response `202 Accepted`:**
```json
{
  "indexing_status": "in_progress",
  "document_count": 140,
  "estimated_completion": "2026-03-20T13:00:00Z"
}
```

---

## Admin — Test Query API

### Endpoint: `POST /v1/admin/test-query`

**Purpose:** Preview how the chatbot would answer a question, optionally comparing before/after a document change (FR-032)
**Auth required:** Yes
**Required role:** Admin

**Request body:**
```json
{
  "query": "string (required, max 2000 chars)",
  "draft_document_id": "uuid (optional) — include a not-yet-published document revision in the search"
}
```

**Response `200 OK`:**
```json
{
  "live_answer": {
    "content": "The current policy states...",
    "citations": [ ... ],
    "intent": { "type": "factual", "domain": "HR", "confidence": 0.92 }
  },
  "preview_answer": {
    "content": "With the updated document, the policy states...",
    "citations": [ ... ],
    "intent": { "type": "factual", "domain": "HR", "confidence": 0.95 }
  }
}
```

If `draft_document_id` is not provided, only `live_answer` is returned and
`preview_answer` is `null`.

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Missing query |
| `401` | Unauthenticated |
| `403` | Not an admin |
| `404` | draft_document_id not found |

---

## Admin — Analytics API

### Endpoint: `GET /v1/admin/analytics/summary`

**Purpose:** Retrieve dashboard summary metrics (FR-029)
**Auth required:** Yes
**Required role:** Admin

**Request:**
```
Query params:
  period: string (optional, default "7d") — "1d", "7d", "30d", "90d"
```

**Response `200 OK`:**
```json
{
  "period": "7d",
  "total_queries": 1423,
  "resolution_rate": 0.87,
  "escalation_rate": 0.08,
  "average_satisfaction": 4.2,
  "no_match_rate": 0.05,
  "daily_volumes": [
    { "date": "2026-03-14", "count": 198 },
    { "date": "2026-03-15", "count": 212 }
  ]
}
```

---

### Endpoint: `GET /v1/admin/analytics/top-intents`

**Purpose:** Retrieve the top 20 most frequent intents (FR-029)
**Auth required:** Yes
**Required role:** Admin

**Request:**
```
Query params:
  period: string (optional, default "7d")
  limit: integer (optional, default 20, max 50)
```

**Response `200 OK`:**
```json
{
  "data": [
    {
      "intent": "PTO policy",
      "domain": "HR",
      "count": 87,
      "resolution_rate": 0.94
    },
    {
      "intent": "Parking badge request",
      "domain": "Facilities",
      "count": 63,
      "resolution_rate": 0.89
    }
  ]
}
```

---

### Endpoint: `GET /v1/admin/analytics/unanswered`

**Purpose:** Retrieve log of queries that could not be matched to a policy (FR-029)
**Auth required:** Yes
**Required role:** Admin

**Request:**
```
Query params:
  cursor: string (optional)
  limit: integer (optional, default 20, max 100)
  period: string (optional, default "7d")
```

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "uuid",
      "query_text": "What's the policy on bringing dogs to the office?",
      "detected_intent": "pet policy",
      "detected_domain": "Facilities",
      "timestamp": "2026-03-19T14:22:00Z"
    }
  ],
  "next_cursor": "string | null"
}
```

---

### Endpoint: `GET /v1/admin/analytics/flagged-topics`

**Purpose:** Retrieve topics flagged due to repeated negative feedback (FR-030)
**Auth required:** Yes
**Required role:** Admin

**Request:**
```
Query params:
  cursor: string (optional)
  limit: integer (optional, default 20, max 100)
```

**Response `200 OK`:**
```json
{
  "data": [
    {
      "topic": "Remote work policy — equipment reimbursement",
      "domain": "IT",
      "negative_count": 7,
      "sample_comments": [
        "This answer is outdated — the policy changed in January",
        "The reimbursement amount listed is wrong"
      ],
      "first_flagged_at": "2026-03-10T09:00:00Z"
    }
  ],
  "next_cursor": "string | null"
}
```

---

## Admin — Coverage Report API

### Endpoint: `GET /v1/admin/coverage`

**Purpose:** Display policy coverage by domain — which categories have indexed content (FR-033)
**Auth required:** Yes
**Required role:** Admin

**Response `200 OK`:**
```json
{
  "categories": [
    {
      "category": "HR",
      "document_count": 42,
      "total_pages": 2840,
      "last_indexed_at": "2026-03-19T14:00:00Z",
      "status": "covered"
    },
    {
      "category": "Safety",
      "document_count": 0,
      "total_pages": 0,
      "last_indexed_at": null,
      "status": "gap"
    }
  ],
  "total_documents": 138,
  "total_pages": 7200,
  "categories_with_gaps": ["Safety"]
}
```

---

## User Profile API

### Endpoint: `GET /v1/me`

**Purpose:** Retrieve the authenticated user's profile for personalization (FR-011)
**Auth required:** Yes
**Required role:** Employee or Admin

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "email": "john.doe@acme.com",
  "first_name": "John",
  "last_name": "Doe",
  "department": "Engineering",
  "location": "HQ Campus",
  "role": "Employee",
  "manager": "jane.smith@acme.com"
}
```

---

## Endpoint Summary

| Method | Path | Role | FR Coverage |
|--------|------|------|-------------|
| `GET` | `/health` | Public | Security Policy |
| `GET` | `/ready` | Public | Security Policy |
| `POST` | `/v1/chat` | Employee, Admin | FR-007–FR-021 |
| `POST` | `/v1/chat/escalate` | Employee, Admin | FR-025, FR-026 |
| `GET` | `/v1/conversations` | Employee, Admin | NFR-010 |
| `GET` | `/v1/conversations/{id}` | Employee, Admin | NFR-010 |
| `POST` | `/v1/feedback` | Employee, Admin | FR-028, FR-030 |
| `GET` | `/v1/me` | Employee, Admin | FR-011 |
| `GET` | `/v1/admin/documents` | Admin | FR-031 |
| `GET` | `/v1/admin/documents/{id}` | Admin | FR-006, FR-031 |
| `POST` | `/v1/admin/documents` | Admin | FR-001, FR-031 |
| `PUT` | `/v1/admin/documents/{id}` | Admin | FR-005, FR-006 |
| `PATCH` | `/v1/admin/documents/{id}` | Admin | FR-031 |
| `POST` | `/v1/admin/documents/{id}/reindex` | Admin | FR-005 |
| `POST` | `/v1/admin/reindex` | Admin | FR-005 |
| `POST` | `/v1/admin/test-query` | Admin | FR-032 |
| `GET` | `/v1/admin/analytics/summary` | Admin | FR-029 |
| `GET` | `/v1/admin/analytics/top-intents` | Admin | FR-029 |
| `GET` | `/v1/admin/analytics/unanswered` | Admin | FR-029 |
| `GET` | `/v1/admin/analytics/flagged-topics` | Admin | FR-030 |
| `GET` | `/v1/admin/coverage` | Admin | FR-033 |
