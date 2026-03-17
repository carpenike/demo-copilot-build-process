# Wireframe Spec: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-17
> **Produced by:** Design Agent
> **Input:** `projects/policy-chatbot/requirements/requirements.md`
> **Related ADRs:** ADR-0007, ADR-0008, ADR-0009, ADR-0010, ADR-0011

---

## API Endpoints

### Authentication

**Mechanism:** Microsoft Entra ID OAuth 2.0 / OIDC (ADR-0011)

**Bot channel traffic:** Authenticated via Bot Framework token validation
(Azure Bot Service handles token exchange for Teams and Direct Line).

**Admin API traffic:** Bearer token from Entra ID with `PolicyAdmin` app role.

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <Entra ID JWT>` |

Error responses (all endpoints unless noted):
- `401 Unauthorized` — missing or invalid token
- `403 Forbidden` — valid token but insufficient role (e.g., non-admin accessing admin endpoints)

---

### Health & Readiness

#### `GET /health`

**Purpose:** Liveness check — indicates the process is running.
**Auth required:** No

**Response `200 OK`:**
```json
{
  "status": "healthy"
}
```

---

#### `GET /ready`

**Purpose:** Readiness check — indicates all dependencies are reachable.
**Auth required:** No

**Response `200 OK`:**
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "azure_openai": "ok",
    "ai_search": "ok"
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
    "azure_openai": "unavailable",
    "ai_search": "ok"
  }
}
```

---

### Bot Framework Endpoint

#### `POST /api/messages`

**Purpose:** Receives all incoming messages from Azure Bot Service (Teams and
Direct Line channels). This endpoint implements the Bot Framework protocol and
is not called directly by clients.
**Auth required:** Yes (Bot Framework auth — validated by Bot Framework SDK)

**Request:** Bot Framework Activity object (handled by SDK)

**Response:** Bot Framework Activity response (handled by SDK)

This endpoint is documented for completeness. The Bot Framework SDK handles
serialization/deserialization. Internally, it routes to the chat pipeline.

---

### Chat API

#### `POST /api/v1/chat`

**Purpose:** Send a message and receive a chatbot response. Used by the web
chat widget as an alternative to Bot Framework Direct Line (for simpler
integrations).
**Auth required:** Yes (Entra ID Bearer token — Employee or PolicyAdmin role)

**Request body:**
```json
{
  "conversation_id": "uuid (optional — omit to start new conversation)",
  "message": "string (required, max 2000 chars)"
}
```

**Response `200 OK`:**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "response": {
    "content": "string — the chatbot's answer text",
    "citations": [
      {
        "document_title": "Bereavement Leave Policy",
        "section": "Section 3.2 — Eligibility",
        "effective_date": "2025-06-01",
        "source_url": "https://intranet.acme.com/policies/hr/bereavement-leave"
      }
    ],
    "checklist": null,
    "disclaimer": "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version.",
    "intent": {
      "domain": "HR",
      "type": "factual"
    },
    "confidence": 0.92,
    "escalated": false
  }
}
```

**Response `200 OK` (procedural query with checklist):**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "response": {
    "content": "Here's how to request FMLA leave:",
    "citations": [
      {
        "document_title": "Family and Medical Leave Policy",
        "section": "Section 5 — Request Procedure",
        "effective_date": "2025-01-15",
        "source_url": "https://intranet.acme.com/policies/hr/fmla"
      }
    ],
    "checklist": {
      "steps": [
        {
          "step_number": 1,
          "text": "Notify your direct manager at least 30 days before the anticipated leave start date",
          "type": "manual",
          "details": "If the leave is unforeseeable, notify as soon as practicable."
        },
        {
          "step_number": 2,
          "text": "Submit the FMLA Request Form in Workday",
          "type": "assisted",
          "link": "https://workday.acme.com/fmla-request",
          "link_label": "Open FMLA Request Form"
        },
        {
          "step_number": 3,
          "text": "Obtain medical certification from your healthcare provider",
          "type": "manual",
          "details": "The certification form is available from Benefits. It must be returned within 15 calendar days."
        },
        {
          "step_number": 4,
          "text": "Contact the Benefits team to confirm leave details",
          "type": "assisted",
          "contact": {
            "name": "Benefits Team",
            "email": "benefits@acme.com",
            "phone": "+1-555-0199",
            "office": "Building A, Room 102"
          }
        },
        {
          "step_number": 5,
          "text": "Visit the HR office to sign leave acknowledgment documents",
          "type": "assisted",
          "wayfinding": {
            "building": "Building A",
            "room": "Room 102",
            "floor": 1,
            "campus_map_url": "https://maps.acme.com/campus/hq?dest=A-102"
          }
        }
      ]
    },
    "disclaimer": "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version.",
    "intent": {
      "domain": "HR",
      "type": "procedural"
    },
    "confidence": 0.88,
    "escalated": false
  }
}
```

**Response `200 OK` (sensitive topic — escalation):**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "response": {
    "content": "This sounds like it may be a sensitive matter. I want to make sure you get the right support. Let me connect you directly with HR.",
    "citations": [],
    "checklist": null,
    "disclaimer": null,
    "intent": {
      "domain": "HR",
      "type": "sensitive"
    },
    "confidence": null,
    "escalated": true,
    "escalation": {
      "reason": "sensitive_topic",
      "servicenow_incident_id": "INC-2026-4521"
    }
  }
}
```

**Response `200 OK` (no policy found):**
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "response": {
    "content": "I wasn't able to find a policy covering that topic. Would you like me to connect you with HR support?",
    "citations": [],
    "checklist": null,
    "disclaimer": "This information is based on current corporate policy and is not legal advice. Policy details may have changed — verify the source document for the most current version.",
    "intent": {
      "domain": null,
      "type": "factual"
    },
    "confidence": 0.15,
    "escalated": false
  }
}
```

**Error responses:**
| Status | Condition | RFC 7807 Type |
|--------|-----------|---------------|
| `400` | Message exceeds 2000 chars or empty | `validation_error` |
| `401` | Unauthenticated | `authentication_required` |
| `429` | Rate limit exceeded | `rate_limit_exceeded` |

---

#### `POST /api/v1/chat/{conversation_id}/escalate`

**Purpose:** Explicitly escalate a conversation to a live service desk agent.
**Auth required:** Yes (Employee or PolicyAdmin)

**Request body:**
```json
{
  "reason": "string (optional — user-provided reason)"
}
```

**Response `200 OK`:**
```json
{
  "conversation_id": "uuid",
  "escalation": {
    "servicenow_incident_id": "INC-2026-4522",
    "message": "I've connected you with our support team. They have your conversation history so you won't need to repeat yourself. Reference: INC-2026-4522"
  }
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `404` | Conversation not found or not owned by this user |

---

#### `POST /api/v1/chat/{conversation_id}/feedback`

**Purpose:** Submit feedback on a specific assistant message.
**Auth required:** Yes (Employee or PolicyAdmin)

**Request body:**
```json
{
  "message_id": "uuid (required — the assistant message being rated)",
  "rating": "positive | negative (required)",
  "comment": "string (optional, max 1000 chars)"
}
```

**Response `201 Created`:**
```json
{
  "feedback_id": "uuid",
  "message_id": "uuid",
  "rating": "negative",
  "comment": "The policy has changed since this was indexed"
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Invalid rating value or missing message_id |
| `404` | Message not found or not in this conversation |
| `409` | Feedback already submitted for this message |

---

### Admin API

All admin endpoints require `PolicyAdmin` app role in the Entra ID token.

#### `GET /api/admin/documents`

**Purpose:** List all policy documents with metadata and status.
**Auth required:** Yes (PolicyAdmin)

**Request:**
```
Query params:
  cursor: string (optional) — pagination cursor
  limit: integer (optional, default 20, max 100)
  category: string (optional) — filter by policy domain
  status: string (optional) — filter by status (active, retired, processing)
```

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "uuid",
      "title": "Bereavement Leave Policy",
      "document_external_id": "HR-POL-042",
      "category": "HR",
      "effective_date": "2025-06-01",
      "review_date": "2026-06-01",
      "owner": "HR Policy Team",
      "source_url": "https://intranet.acme.com/policies/hr/bereavement-leave",
      "status": "active",
      "current_version": 2,
      "created_at": "2026-03-15T10:30:00Z",
      "updated_at": "2026-03-15T14:22:00Z"
    }
  ],
  "next_cursor": "string | null",
  "total": 142
}
```

---

#### `POST /api/admin/documents`

**Purpose:** Upload a new policy document and trigger indexing.
**Auth required:** Yes (PolicyAdmin)

**Request:** `multipart/form-data`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `file` | File | Yes | PDF, DOCX, or HTML (max 50 MB) |
| `title` | string | Yes | Document title |
| `document_external_id` | string | Yes | External reference ID |
| `category` | string | Yes | One of: HR, IT, Finance, Facilities, Legal, Compliance, Safety |
| `effective_date` | date | Yes | ISO 8601 date |
| `review_date` | date | No | Next review date |
| `owner` | string | Yes | Policy owner |
| `source_url` | string | No | Link to source in SharePoint/intranet |

**Response `202 Accepted`:**
```json
{
  "id": "uuid",
  "title": "New Travel Policy",
  "status": "processing",
  "version": 1,
  "message": "Document uploaded. Indexing has been queued and will complete shortly."
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Missing required fields, unsupported file format, or file too large |
| `409` | Document with this `document_external_id` already exists |

---

#### `PUT /api/admin/documents/{document_id}`

**Purpose:** Upload a new version of an existing document and trigger re-indexing.
**Auth required:** Yes (PolicyAdmin)

**Request:** `multipart/form-data` (same fields as POST, file required)

**Response `202 Accepted`:**
```json
{
  "id": "uuid",
  "title": "Updated Travel Policy",
  "status": "processing",
  "version": 3,
  "message": "New version uploaded. Re-indexing has been queued."
}
```

---

#### `POST /api/admin/documents/{document_id}/retire`

**Purpose:** Retire a document from the active corpus.
**Auth required:** Yes (PolicyAdmin)

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "title": "Old Travel Policy",
  "status": "retired",
  "message": "Document retired. It will no longer be used in chatbot answers."
}
```

---

#### `POST /api/admin/documents/{document_id}/reindex`

**Purpose:** Trigger re-indexing of a single document.
**Auth required:** Yes (PolicyAdmin)

**Response `202 Accepted`:**
```json
{
  "id": "uuid",
  "status": "processing",
  "message": "Re-indexing queued."
}
```

---

#### `POST /api/admin/reindex-all`

**Purpose:** Trigger full corpus re-indexing.
**Auth required:** Yes (PolicyAdmin)

**Response `202 Accepted`:**
```json
{
  "status": "processing",
  "total_documents": 142,
  "message": "Full corpus re-indexing has been queued. This may take up to 2 hours."
}
```

---

#### `GET /api/admin/reindex-status`

**Purpose:** Check the status of an ongoing re-indexing operation.
**Auth required:** Yes (PolicyAdmin)

**Response `200 OK`:**
```json
{
  "status": "in_progress",
  "documents_processed": 87,
  "documents_total": 142,
  "started_at": "2026-03-17T14:00:00Z",
  "estimated_completion": "2026-03-17T15:30:00Z"
}
```

---

#### `GET /api/admin/documents/{document_id}/versions`

**Purpose:** View version history of a document.
**Auth required:** Yes (PolicyAdmin)

**Response `200 OK`:**
```json
{
  "document_id": "uuid",
  "versions": [
    {
      "version_number": 2,
      "status": "indexed",
      "indexed_by": "admin@acme.com",
      "indexed_at": "2026-03-15T14:22:00Z",
      "created_at": "2026-03-15T14:00:00Z"
    },
    {
      "version_number": 1,
      "status": "superseded",
      "indexed_by": "admin@acme.com",
      "indexed_at": "2026-03-01T10:00:00Z",
      "created_at": "2026-03-01T09:45:00Z"
    }
  ]
}
```

---

#### `POST /api/admin/test-query`

**Purpose:** Test how the chatbot would answer a question. Optionally test
against a staged (not-yet-published) document version.
**Auth required:** Yes (PolicyAdmin)

**Request body:**
```json
{
  "query": "string (required — the test question)",
  "staged_document_id": "uuid (optional — test with a staged document version)"
}
```

**Response `200 OK`:**
```json
{
  "live_response": {
    "content": "Current live answer text...",
    "citations": [...],
    "confidence": 0.88
  },
  "staged_response": {
    "content": "Answer with staged document version...",
    "citations": [...],
    "confidence": 0.91
  }
}
```

If `staged_document_id` is not provided, `staged_response` is `null`.

---

#### `GET /api/admin/coverage`

**Purpose:** Display policy domain coverage report.
**Auth required:** Yes (PolicyAdmin)

**Response `200 OK`:**
```json
{
  "categories": [
    {"name": "HR", "document_count": 42, "status": "covered"},
    {"name": "IT", "document_count": 28, "status": "covered"},
    {"name": "Finance", "document_count": 18, "status": "covered"},
    {"name": "Facilities", "document_count": 22, "status": "covered"},
    {"name": "Legal", "document_count": 15, "status": "covered"},
    {"name": "Compliance", "document_count": 12, "status": "covered"},
    {"name": "Safety", "document_count": 5, "status": "covered"}
  ],
  "total_documents": 142,
  "gaps": []
}
```

---

#### `GET /api/admin/analytics`

**Purpose:** Retrieve analytics dashboard data.
**Auth required:** Yes (PolicyAdmin)

**Request:**
```
Query params:
  start_date: date (required) — ISO 8601
  end_date: date (required) — ISO 8601
  granularity: string (optional, default "daily") — "daily" | "weekly" | "monthly"
```

**Response `200 OK`:**
```json
{
  "period": {
    "start_date": "2026-03-01",
    "end_date": "2026-03-17",
    "granularity": "daily"
  },
  "summary": {
    "total_queries": 4521,
    "resolution_rate": 0.78,
    "escalation_rate": 0.12,
    "average_satisfaction": 4.2,
    "unanswered_count": 87
  },
  "top_intents": [
    {"intent": "PTO policy", "count": 342},
    {"intent": "Parking badge request", "count": 287},
    {"intent": "Bereavement leave", "count": 198}
  ],
  "volume_by_period": [
    {"date": "2026-03-01", "count": 245},
    {"date": "2026-03-02", "count": 312}
  ]
}
```

---

#### `GET /api/admin/analytics/unanswered`

**Purpose:** View log of unanswered queries.
**Auth required:** Yes (PolicyAdmin)

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
      "query": "What is the policy on pet insurance?",
      "attempted_domain": null,
      "count": 5,
      "last_asked": "2026-03-17T09:15:00Z"
    }
  ],
  "next_cursor": "string | null"
}
```

---

#### `GET /api/admin/analytics/flagged`

**Purpose:** View topics flagged for review due to repeated negative feedback.
**Auth required:** Yes (PolicyAdmin)

**Response `200 OK`:**
```json
{
  "flagged_topics": [
    {
      "topic": "Remote work policy",
      "negative_feedback_count": 7,
      "sample_queries": [
        "What is the remote work policy?",
        "Can I work from home permanently?"
      ],
      "sample_comments": [
        "This policy was updated last month",
        "Missing information about hybrid schedules"
      ]
    }
  ]
}
```

---

## Error Response Format

All error responses follow RFC 7807 Problem Details:

```json
{
  "type": "validation_error",
  "title": "Bad Request",
  "status": 400,
  "detail": "Message must be between 1 and 2000 characters.",
  "instance": "/api/v1/chat"
}
```

---

## Rate Limiting

| Endpoint Group | Limit | Window |
|----------------|-------|--------|
| Chat API (`/api/v1/chat`) | 30 requests/minute per user | Sliding window |
| Admin API (`/api/admin/*`) | 60 requests/minute per user | Sliding window |
| Health endpoints | No limit | — |

Rate limit headers included in all responses:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 28
X-RateLimit-Reset: 1710680460
```
