# Wireframe Spec: Support Ticket Portal

> **Version:** 1.0
> **Date:** 2026-03-13
> **Produced by:** Design Agent
> **Input:** `projects/example-ticket-app/requirements/requirements.md`
> **Related ADRs:** ADR-0001, ADR-0002, ADR-0003

---

## API Endpoints

### Authentication

**Mechanism:** JWT Bearer tokens (OAuth2 provider, per NFR-004)

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <token>` |

Error responses:
- `401 Unauthorized` — missing or invalid token
- `403 Forbidden` — valid token but insufficient role

### Roles
- `customer` — can manage own tickets only
- `agent` — can manage all tickets, add internal notes
- `admin` — agent permissions + dashboard + export

---

### Endpoint: `POST /v1/tickets`

**Purpose:** Submit a new support ticket
**Auth required:** Yes
**Required role:** `customer`

**Request body:**
```json
{
  "subject": "string (required, max 255 chars)",
  "description": "string (required, max 10000 chars)",
  "priority": "string (required, enum: low | medium | high)"
}
```

**Response `201 Created`:**
```json
{
  "id": "uuid",
  "ticket_number": "TKT-001",
  "subject": "Login page returns 500",
  "description": "When I try to...",
  "priority": "high",
  "status": "open",
  "customer_id": "uuid",
  "assigned_agent_id": null,
  "created_at": "2026-03-13T10:00:00Z",
  "updated_at": "2026-03-13T10:00:00Z"
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Validation error (missing field, invalid priority) |
| `401` | Unauthenticated |

---

### Endpoint: `GET /v1/tickets`

**Purpose:** List tickets (customers see own; agents see all)
**Auth required:** Yes
**Required role:** `customer`, `agent`

**Request:**
```
Query params:
  status: string (optional, enum: open | in_progress | waiting | resolved | closed)
  priority: string (optional, enum: low | medium | high)
  assigned_agent_id: uuid (optional, agent role only)
  q: string (optional, full-text search query)
  date_from: date (optional, ISO 8601)
  date_to: date (optional, ISO 8601)
  cursor: string (optional, pagination cursor)
  limit: integer (optional, default 20, max 100)
```

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "uuid",
      "ticket_number": "TKT-001",
      "subject": "Login page returns 500",
      "priority": "high",
      "status": "open",
      "customer_id": "uuid",
      "assigned_agent_id": "uuid | null",
      "created_at": "2026-03-13T10:00:00Z",
      "updated_at": "2026-03-13T10:15:00Z"
    }
  ],
  "next_cursor": "string | null",
  "total": 42
}
```

---

### Endpoint: `GET /v1/tickets/{ticket_id}`

**Purpose:** Get ticket detail with comments
**Auth required:** Yes
**Required role:** `customer` (own only), `agent`

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "ticket_number": "TKT-001",
  "subject": "Login page returns 500",
  "description": "Full description...",
  "priority": "high",
  "status": "in_progress",
  "customer_id": "uuid",
  "assigned_agent_id": "uuid",
  "created_at": "2026-03-13T10:00:00Z",
  "updated_at": "2026-03-13T10:15:00Z",
  "comments": [
    {
      "id": "uuid",
      "author_id": "uuid",
      "author_role": "customer",
      "body": "Here are the logs...",
      "is_internal": false,
      "created_at": "2026-03-13T10:30:00Z"
    }
  ],
  "attachments": [
    {
      "id": "uuid",
      "filename": "error-screenshot.png",
      "size_bytes": 245000,
      "content_type": "image/png",
      "upload_url": "https://..."
    }
  ]
}
```

> **Note:** `is_internal: true` comments are filtered out when the requester's
> role is `customer`.

**Error responses:**
| Status | Condition |
|--------|-----------|
| `403` | Customer trying to access another customer's ticket |
| `404` | Ticket not found |

---

### Endpoint: `PATCH /v1/tickets/{ticket_id}`

**Purpose:** Update ticket (status, assignment)
**Auth required:** Yes
**Required role:** `agent`

**Request body:**
```json
{
  "status": "string (optional, enum: open | in_progress | waiting | resolved | closed)",
  "assigned_agent_id": "uuid (optional)"
}
```

**Response `200 OK`:** Updated ticket object (same shape as GET)

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Invalid status transition |
| `403` | Customer attempting to update |
| `404` | Ticket not found |

**Valid status transitions:**
```
open → in_progress
open → closed
in_progress → waiting
in_progress → resolved
waiting → in_progress
resolved → closed
resolved → open (reopen)
```

---

### Endpoint: `POST /v1/tickets/{ticket_id}/comments`

**Purpose:** Add a comment (customer visible) or internal note (agent only)
**Auth required:** Yes
**Required role:** `customer`, `agent`

**Request body:**
```json
{
  "body": "string (required, max 5000 chars)",
  "is_internal": "boolean (default false, ignored if role is customer)"
}
```

**Response `201 Created`:**
```json
{
  "id": "uuid",
  "author_id": "uuid",
  "author_role": "agent",
  "body": "Checked the database logs...",
  "is_internal": true,
  "created_at": "2026-03-13T11:00:00Z"
}
```

---

### Endpoint: `POST /v1/tickets/{ticket_id}/attachments`

**Purpose:** Upload a file attachment to a ticket
**Auth required:** Yes
**Required role:** `customer` (own ticket only), `agent`

**Request:** `multipart/form-data` with file field
- Max file size: 10MB
- Accepted types: image/jpeg, image/png, application/pdf, text/plain
- Max 5 attachments per ticket

**Response `201 Created`:**
```json
{
  "id": "uuid",
  "filename": "receipt.pdf",
  "size_bytes": 52000,
  "content_type": "application/pdf"
}
```

---

### Endpoint: `GET /v1/tickets/export`

**Purpose:** Export filtered ticket list as CSV
**Auth required:** Yes
**Required role:** `agent`, `admin`

**Request:** Same query params as `GET /v1/tickets`

**Response `200 OK`:**
- `Content-Type: text/csv`
- `Content-Disposition: attachment; filename="tickets-export-2026-03-13.csv"`

---

### Endpoint: `GET /v1/dashboard/metrics`

**Purpose:** Aggregated reporting metrics
**Auth required:** Yes
**Required role:** `admin`

**Request:**
```
Query params:
  period: string (required, enum: day | week | month)
  date_from: date (required, ISO 8601)
  date_to: date (required, ISO 8601)
```

**Response `200 OK`:**
```json
{
  "period": "week",
  "ticket_volume": {
    "total": 142,
    "by_status": {"open": 23, "in_progress": 45, "resolved": 60, "closed": 14},
    "by_priority": {"high": 30, "medium": 72, "low": 40}
  },
  "resolution_time": {
    "average_hours": 18.5,
    "median_hours": 12.0,
    "p90_hours": 48.0
  },
  "agent_performance": [
    {
      "agent_id": "uuid",
      "agent_name": "Jane Smith",
      "resolved_count": 28,
      "avg_resolution_hours": 14.2,
      "open_count": 5
    }
  ],
  "generated_at": "2026-03-13T12:00:00Z"
}
```

---

### Required Infrastructure Endpoints

```
GET /health  → 200 {"status": "ok"}
GET /ready   → 200 {"status": "ready"} or 503 if DB/Redis unhealthy
GET /metrics → Prometheus text format
```
