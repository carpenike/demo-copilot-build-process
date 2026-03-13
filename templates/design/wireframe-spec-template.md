# Wireframe Spec: [Project Name]

> **Version:** 1.0
> **Date:** YYYY-MM-DD
> **Produced by:** Design Agent
> **Input:** `projects/<project>/requirements/requirements.md`
> **Related ADRs:** ADR-XXXX, ADR-XXXX

---

## API Endpoints

> Complete this section for API / backend services.
> Reference: `openapi.yaml` will be generated from this spec by the Code Agent.

### Authentication

**Mechanism:** [JWT Bearer / API Key / OAuth2 — as decided in ADR-XXXX]

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <token>` |

Error responses:
- `401 Unauthorized` — missing or invalid token
- `403 Forbidden` — valid token but insufficient permissions

---

### Endpoint: `GET /v1/[resource]`

**Purpose:** [What this endpoint does in plain English]
**Auth required:** Yes / No
**Required permissions:** [permission scope]

**Request:**
```
Query params:
  cursor: string (optional) — pagination cursor from previous response
  limit: integer (optional, default 20, max 100)
```

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "uuid",
      "field_name": "string",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "next_cursor": "string | null",
  "total": 42
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Invalid query parameter |
| `401` | Unauthenticated |
| `403` | Insufficient permissions |

---

### Endpoint: `POST /v1/[resource]`

**Purpose:** [What this endpoint does]
**Auth required:** Yes
**Required permissions:** [scope]

**Request body:**
```json
{
  "field_name": "string (required, max 255 chars)",
  "optional_field": "string (optional)"
}
```

**Response `201 Created`:**
```json
{
  "id": "uuid",
  "field_name": "string",
  "created_at": "2026-01-01T00:00:00Z"
}
```

**Error responses:**
| Status | Condition |
|--------|-----------|
| `400` | Validation error (body includes field-level errors) |
| `409` | Conflict — resource already exists |

---

## UI Screen Inventory

> Complete this section for user-facing applications.

### Screen: [Screen Name]

**Route:** `/path/to/screen`
**Purpose:** [What the user accomplishes on this screen]
**Auth required:** Yes / No

**Data requirements:**
- Loads: [what data is fetched, from which endpoint]
- Writes: [what actions trigger API calls]

**Component hierarchy:**
```
PageLayout
  ├── Header
  │   ├── NavigationBar
  │   └── UserMenu
  ├── MainContent
  │   ├── [ComponentName]
  │   │   ├── [ChildComponent]
  │   │   └── [ChildComponent]
  │   └── [ComponentName]
  └── Footer
```

**User interactions:**
| Interaction | Trigger | Outcome |
|-------------|---------|---------|
| [User clicks X] | Button click | [Opens modal / navigates / calls API] |

**States:**
- Loading: [Skeleton / spinner at which level]
- Empty: [What the user sees with no data]
- Error: [How errors are surfaced]
- Success: [Confirmation pattern]

---

## Navigation & Routing

```
/                       → Landing / Dashboard
/login                  → Authentication screen
/[resource]             → List view
/[resource]/[id]        → Detail view
/[resource]/new         → Create form
/[resource]/[id]/edit   → Edit form
```

---

## Error Handling Patterns

**Inline field validation:** Show error below field on blur
**Form-level errors:** Banner at top of form after failed submit
**Toast notifications:** Success and non-blocking errors
**Full-page errors:** 404 (not found), 403 (forbidden), 500 (unexpected)
