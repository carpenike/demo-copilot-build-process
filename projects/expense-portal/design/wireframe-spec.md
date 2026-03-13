# Wireframe Spec: Employee Expense Management Portal

> **Version:** 1.0
> **Date:** 2026-03-13
> **Produced by:** Design Agent
> **Input:** `projects/expense-portal/requirements/requirements.md`
> **Related ADRs:** ADR-0004, ADR-0005, ADR-0006, ADR-0007, ADR-0008

---

## API Endpoints

### Authentication

**Mechanism:** Microsoft Entra ID OIDC (Authorization Code + PKCE) — see ADR-0006

| Header | Value |
|--------|-------|
| Cookie | `session=<server-side session ID>` (HttpOnly, Secure, SameSite=Lax) |

Error responses:
- `401 Unauthorized` — session missing, expired, or invalid
- `403 Forbidden` — valid session but insufficient role/permissions

All error responses use RFC 7807 Problem Details format (NFR-023):
```json
{
  "type": "https://expenses.acme.com/errors/forbidden",
  "title": "Forbidden",
  "status": 403,
  "detail": "You do not have permission to view this resource.",
  "instance": "/v1/expenses/reports/abc-123"
}
```

---

### Auth Endpoints

#### `GET /v1/auth/login`

**Purpose:** Initiate OIDC login flow — redirects to Microsoft Entra ID
**Auth required:** No

**Response:** `302 Found` → Entra ID authorization endpoint

---

#### `GET /v1/auth/callback`

**Purpose:** OIDC callback — exchanges authorization code for tokens, creates session
**Auth required:** No

**Response:** `302 Found` → `/` (dashboard) with session cookie set

---

#### `POST /v1/auth/logout`

**Purpose:** Destroy session, redirect to Entra ID logout
**Auth required:** Yes

**Response:** `302 Found` → Entra ID logout endpoint

---

### Expense Report Endpoints

#### `GET /v1/expenses/reports`

**Purpose:** List the current user's expense reports (Employee) or direct reports' expense reports (Manager)
**Auth required:** Yes
**Required permissions:** Employee (own reports), Manager (direct reports' reports)

**Request:**
```
Query params:
  cursor: string (optional) — pagination cursor
  limit: integer (optional, default 20, max 100)
  status: string (optional) — filter by status: draft, submitted, manager_approved,
          finance_review, approved, rejected, information_requested, payment_processing
  date_from: date (optional, ISO 8601) — filter reports with end_date >= date_from
  date_to: date (optional, ISO 8601) — filter reports with start_date <= date_to
```

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "uuid",
      "title": "Q1 Client Meetings",
      "status": "submitted",
      "start_date": "2026-03-01",
      "end_date": "2026-03-07",
      "business_purpose": "Client meetings in Seattle",
      "total_amount": 847.50,
      "currency": "USD",
      "line_item_count": 5,
      "submitted_at": "2026-03-08T14:30:00Z",
      "submitter": {
        "id": "uuid",
        "name": "Jane Smith",
        "cost_center": "Engineering"
      },
      "created_at": "2026-03-07T09:00:00Z",
      "updated_at": "2026-03-08T14:30:00Z"
    }
  ],
  "next_cursor": "eyJpZCI6IjEyMyJ9",
  "total": 42
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| `400` | Invalid query parameter (bad date format, invalid status) |
| `401` | Unauthenticated |

---

#### `POST /v1/expenses/reports`

**Purpose:** Create a new expense report (draft or submitted)
**Auth required:** Yes
**Required permissions:** Employee

**Request body:**
```json
{
  "title": "string (required, max 255 chars)",
  "start_date": "2026-03-01 (required, ISO 8601 date)",
  "end_date": "2026-03-07 (required, ISO 8601 date, >= start_date)",
  "business_purpose": "string (required, max 1000 chars)",
  "submit": false
}
```

**Response `201 Created`:**
```json
{
  "id": "uuid",
  "title": "Q1 Client Meetings",
  "status": "draft",
  "start_date": "2026-03-01",
  "end_date": "2026-03-07",
  "business_purpose": "Client meetings in Seattle",
  "total_amount": 0,
  "currency": "USD",
  "line_item_count": 0,
  "created_at": "2026-03-07T09:00:00Z",
  "updated_at": "2026-03-07T09:00:00Z"
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| `400` | Validation error (missing required field, end_date < start_date) |
| `401` | Unauthenticated |

---

#### `GET /v1/expenses/reports/{report_id}`

**Purpose:** Get full details of a single expense report including all line items
**Auth required:** Yes
**Required permissions:** Owner of the report, or Manager of the submitter, or Finance Reviewer

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "title": "Q1 Client Meetings",
  "status": "submitted",
  "start_date": "2026-03-01",
  "end_date": "2026-03-07",
  "business_purpose": "Client meetings in Seattle",
  "total_amount": 847.50,
  "currency": "USD",
  "submitter": {
    "id": "uuid",
    "name": "Jane Smith",
    "cost_center": "Engineering",
    "cost_center_id": "uuid"
  },
  "line_items": [
    {
      "id": "uuid",
      "date": "2026-03-01",
      "category": "Meals",
      "vendor_name": "Café Luna",
      "amount": 42.50,
      "currency": "USD",
      "description": "Lunch with client",
      "receipt_url": "https://expenses.acme.com/v1/receipts/uuid",
      "policy_violations": [],
      "ocr_status": "completed"
    }
  ],
  "approval_history": [
    {
      "action": "submitted",
      "actor": "Jane Smith",
      "timestamp": "2026-03-08T14:30:00Z",
      "comment": null
    }
  ],
  "policy_violations_summary": {
    "blocking": 0,
    "warnings": 1
  },
  "created_at": "2026-03-07T09:00:00Z",
  "updated_at": "2026-03-08T14:30:00Z"
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| `401` | Unauthenticated |
| `403` | User is not the owner, manager of the submitter, or Finance Reviewer |
| `404` | Report not found |

---

#### `PATCH /v1/expenses/reports/{report_id}`

**Purpose:** Update an expense report (only in draft or rejected status)
**Auth required:** Yes
**Required permissions:** Owner of the report

**Request body:**
```json
{
  "title": "string (optional)",
  "start_date": "date (optional)",
  "end_date": "date (optional)",
  "business_purpose": "string (optional)"
}
```

**Response `200 OK`:** Updated report object (same schema as GET)

**Error responses:**

| Status | Condition |
|--------|-----------|
| `400` | Validation error |
| `401` | Unauthenticated |
| `403` | Not the owner |
| `409` | Report is not in draft or rejected status (cannot edit after submission) |

---

#### `POST /v1/expenses/reports/{report_id}/submit`

**Purpose:** Submit a draft or rejected report for approval. Triggers policy validation and duplicate detection.
**Auth required:** Yes
**Required permissions:** Owner of the report

**Request body:**
```json
{
  "acknowledge_warnings": false
}
```

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "status": "submitted",
  "submitted_at": "2026-03-08T14:30:00Z",
  "routed_to": {
    "id": "uuid",
    "name": "Bob Manager"
  }
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| `400` | Report has no line items |
| `401` | Unauthenticated |
| `403` | Not the owner |
| `409` | Report is not in draft or rejected status |
| `422` | Policy violations block submission (response includes `violations` array) |

Policy violation response (`422`):
```json
{
  "type": "https://expenses.acme.com/errors/policy-violation",
  "title": "Policy Violations",
  "status": 422,
  "detail": "2 policy violations must be resolved before submission.",
  "violations": [
    {
      "line_item_id": "uuid",
      "rule": "per_diem_exceeded",
      "message": "Meals amount $125.00 exceeds daily limit of $75.00",
      "blocking": true
    },
    {
      "line_item_id": "uuid",
      "rule": "duplicate_detected",
      "message": "Possible duplicate: $42.50 at Café Luna on 2026-03-01 matches report RPT-0042",
      "blocking": false
    }
  ]
}
```

---

### Line Item Endpoints

#### `POST /v1/expenses/reports/{report_id}/line-items`

**Purpose:** Add a line item to an expense report
**Auth required:** Yes
**Required permissions:** Owner of the report (report must be in draft or rejected status)

**Request body:**
```json
{
  "date": "2026-03-01 (required, ISO 8601 date)",
  "category": "string (required — must match a configured category)",
  "vendor_name": "string (required, max 255 chars)",
  "amount": 42.50,
  "currency": "USD (required, USD or CAD)",
  "description": "string (required, max 500 chars)"
}
```

**Response `201 Created`:**
```json
{
  "id": "uuid",
  "date": "2026-03-01",
  "category": "Meals",
  "vendor_name": "Café Luna",
  "amount": 42.50,
  "currency": "USD",
  "description": "Lunch with client",
  "receipt_url": null,
  "policy_violations": [],
  "ocr_status": null,
  "created_at": "2026-03-07T09:15:00Z"
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| `400` | Validation error (missing field, invalid category, invalid currency) |
| `403` | Not the owner |
| `409` | Report is not in draft or rejected status |

---

#### `PATCH /v1/expenses/reports/{report_id}/line-items/{item_id}`

**Purpose:** Update a line item
**Auth required:** Yes
**Required permissions:** Owner (report in draft or rejected status)

**Request body:** Same fields as POST, all optional

**Response `200 OK`:** Updated line item object

---

#### `DELETE /v1/expenses/reports/{report_id}/line-items/{item_id}`

**Purpose:** Remove a line item from a draft/rejected report
**Auth required:** Yes
**Required permissions:** Owner (report in draft or rejected status)

**Response:** `204 No Content`

---

### Receipt Endpoints

#### `POST /v1/expenses/reports/{report_id}/line-items/{item_id}/receipt`

**Purpose:** Upload a receipt image for a line item. Triggers async OCR processing.
**Auth required:** Yes
**Required permissions:** Owner (report in draft or rejected status)

**Request:** `multipart/form-data`
```
file: binary (required, JPEG/PNG/PDF, max 10 MB)
```

**Response `202 Accepted`:**
```json
{
  "receipt_url": "https://expenses.acme.com/v1/receipts/uuid",
  "ocr_status": "processing",
  "ocr_task_id": "uuid"
}
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| `400` | File too large (>10 MB) or unsupported format |
| `403` | Not the owner |
| `409` | Report is not in draft or rejected status |

---

#### `GET /v1/receipts/{receipt_id}`

**Purpose:** Download a receipt image (returns a time-limited SAS URL redirect)
**Auth required:** Yes
**Required permissions:** Owner, Manager of submitter, or Finance Reviewer

**Response:** `302 Found` → Azure Blob Storage SAS URL (15-minute expiry)

---

#### `GET /v1/expenses/ocr-status/{task_id}`

**Purpose:** Poll OCR processing status for a receipt
**Auth required:** Yes

**Response `200 OK`:**
```json
{
  "task_id": "uuid",
  "status": "completed",
  "extracted_fields": {
    "amount": {"value": 42.50, "confidence": 0.94},
    "vendor_name": {"value": "Café Luna", "confidence": 0.91},
    "date": {"value": "2026-03-01", "confidence": 0.88}
  }
}
```

Status values: `processing`, `completed`, `failed`

---

### Approval Endpoints

#### `GET /v1/approvals/pending`

**Purpose:** List expense reports pending the current user's approval
**Auth required:** Yes
**Required permissions:** Manager or Finance Reviewer

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
      "report_id": "uuid",
      "title": "Q1 Client Meetings",
      "submitter": {"id": "uuid", "name": "Jane Smith"},
      "total_amount": 847.50,
      "line_item_count": 5,
      "submitted_at": "2026-03-08T14:30:00Z",
      "pending_since": "2026-03-08T14:30:00Z",
      "approval_type": "manager"
    }
  ],
  "next_cursor": "eyJpZCI6IjQ1NiJ9",
  "total": 3
}
```

---

#### `POST /v1/approvals/{report_id}/approve`

**Purpose:** Approve an expense report
**Auth required:** Yes
**Required permissions:** Designated approver for this report

**Request body:**
```json
{
  "comment": "string (optional, max 500 chars)"
}
```

**Response `200 OK`:**
```json
{
  "report_id": "uuid",
  "new_status": "manager_approved",
  "next_step": "finance_review",
  "approved_at": "2026-03-09T10:00:00Z"
}
```

---

#### `POST /v1/approvals/{report_id}/reject`

**Purpose:** Reject an expense report
**Auth required:** Yes
**Required permissions:** Designated approver for this report

**Request body:**
```json
{
  "reason": "string (required, max 1000 chars)"
}
```

**Response `200 OK`:**
```json
{
  "report_id": "uuid",
  "new_status": "rejected",
  "rejected_at": "2026-03-09T10:00:00Z"
}
```

---

#### `POST /v1/approvals/{report_id}/request-info`

**Purpose:** Request more information from the submitter
**Auth required:** Yes
**Required permissions:** Designated approver for this report

**Request body:**
```json
{
  "question": "string (required, max 1000 chars)"
}
```

**Response `200 OK`:**
```json
{
  "report_id": "uuid",
  "new_status": "information_requested",
  "requested_at": "2026-03-09T10:00:00Z"
}
```

---

#### `GET /v1/actions/{token}`

**Purpose:** Execute an approval action via email link (single-use, time-bounded)
**Auth required:** Yes (redirects to SSO if not authenticated)

**Flow:**
1. Validate token (exists, not expired, not used)
2. If user not authenticated → redirect to SSO → return to this URL
3. Verify authenticated user matches the designated approver
4. Display confirmation page with report summary and action button
5. On confirmation → execute action, mark token used

**Error responses:**

| Status | Condition |
|--------|-----------|
| `400` | Token expired or already used |
| `403` | Authenticated user is not the designated approver |
| `404` | Token not found |

---

### Dashboard & Reporting Endpoints

#### `GET /v1/reports/finance`

**Purpose:** Finance reporting dashboard data
**Auth required:** Yes
**Required permissions:** Finance Reviewer or Finance Administrator

**Request:**
```
Query params:
  period: string (required — "monthly", "quarterly", "yearly")
  date_from: date (optional)
  date_to: date (optional)
  cost_center_id: uuid (optional)
  category: string (optional)
  status: string (optional)
  format: string (optional — "json" default, "csv")
```

**Response `200 OK`:**
```json
{
  "summary": {
    "total_amount": 245000.00,
    "report_count": 312,
    "average_amount": 785.26,
    "period": "2026-Q1"
  },
  "by_cost_center": [
    {"cost_center": "Engineering", "total": 89000.00, "count": 120},
    {"cost_center": "Sales", "total": 156000.00, "count": 192}
  ],
  "by_category": [
    {"category": "Meals", "total": 45000.00, "count": 380},
    {"category": "Travel", "total": 120000.00, "count": 95}
  ],
  "by_status": [
    {"status": "approved", "total": 200000.00, "count": 265},
    {"status": "pending", "total": 45000.00, "count": 47}
  ]
}
```

When `format=csv`, response is `200` with `Content-Type: text/csv` and `Content-Disposition: attachment`.

---

#### `GET /v1/reports/manager`

**Purpose:** Manager team spend dashboard data
**Auth required:** Yes
**Required permissions:** Manager

**Request:**
```
Query params:
  period: string (optional — defaults to current month)
  format: string (optional — "json" default, "csv")
```

**Response `200 OK`:**
```json
{
  "cost_center": "Engineering",
  "budget": 150000.00,
  "period": "2026-03",
  "total_submitted": 32000.00,
  "total_approved": 28000.00,
  "remaining_budget": 122000.00,
  "by_employee": [
    {
      "employee": {"id": "uuid", "name": "Jane Smith"},
      "submitted": 4500.00,
      "approved": 3200.00,
      "pending": 1300.00
    }
  ]
}
```

---

### Admin Endpoints

#### `GET /v1/admin/categories`

**Purpose:** List expense categories
**Auth required:** Yes
**Required permissions:** Finance Administrator

**Response `200 OK`:**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Meals",
      "daily_limit": 75.00,
      "reimbursable": true,
      "per_diem_rates": [
        {"destination": "US-Domestic", "rate": 75.00},
        {"destination": "US-NYC", "rate": 100.00},
        {"destination": "CA-Domestic", "rate": 80.00}
      ]
    }
  ]
}
```

---

#### `POST /v1/admin/categories`

**Purpose:** Create a new expense category
**Auth required:** Yes
**Required permissions:** Finance Administrator

**Request body:**
```json
{
  "name": "string (required, max 100 chars)",
  "daily_limit": 75.00,
  "reimbursable": true,
  "per_diem_rates": [
    {"destination": "string (required)", "rate": 75.00}
  ]
}
```

**Response:** `201 Created` with category object

---

#### `PATCH /v1/admin/categories/{category_id}`

**Purpose:** Update a category (limit, reimbursable status, per diem rates)
**Auth required:** Yes
**Required permissions:** Finance Administrator

---

#### `GET /v1/admin/approval-thresholds`

**Purpose:** Get current approval threshold settings
**Auth required:** Yes
**Required permissions:** Finance Administrator

**Response `200 OK`:**
```json
{
  "finance_review_threshold": 500.00,
  "auto_escalation_days": 5,
  "reminder_days": 3
}
```

---

#### `PATCH /v1/admin/approval-thresholds`

**Purpose:** Update approval threshold settings
**Auth required:** Yes
**Required permissions:** Finance Administrator

---

### Operational Endpoints

#### `GET /health`

**Purpose:** Kubernetes liveness probe
**Auth required:** No

**Response `200 OK`:** `{"status": "ok"}`

---

#### `GET /ready`

**Purpose:** Kubernetes readiness probe — checks database and Redis connectivity
**Auth required:** No

**Response `200 OK`:** `{"status": "ready", "checks": {"database": "ok", "redis": "ok"}}`
**Response `503 Service Unavailable`:** `{"status": "not_ready", "checks": {"database": "ok", "redis": "error"}}`

---

#### `GET /metrics`

**Purpose:** Prometheus-compatible metrics endpoint
**Auth required:** No (internal network only, not exposed via API gateway)

---

## UI Screen Inventory

### Screen: Login

**Route:** `/login`
**Purpose:** Redirect to Microsoft Entra ID SSO
**Auth required:** No

**User interactions:**

| Interaction | Trigger | Outcome |
|-------------|---------|---------|
| Click "Sign in with SSO" | Button click | Redirects to Entra ID login (GET /v1/auth/login) |

---

### Screen: Employee Dashboard

**Route:** `/`
**Purpose:** Landing page showing the employee's recent expense reports and quick actions
**Auth required:** Yes

**Data requirements:**
- Loads: GET /v1/expenses/reports (own reports, limit 10, sorted by updated_at desc)
- Loads: GET /v1/approvals/pending (if user is a manager — pending approval count badge)

**Component hierarchy:**
```
PageLayout
  ├── Header
  │   ├── NavigationBar [Dashboard, My Expenses, Approvals*, Reports*, Admin*]
  │   └── UserMenu [name, role, logout]
  ├── MainContent
  │   ├── WelcomeBanner
  │   │   └── QuickActions [New Expense Report button]
  │   ├── ApprovalBadge* [pending count — visible for managers]
  │   ├── RecentReports
  │   │   └── ReportCard[] [title, status badge, total, date, action link]
  │   └── DraftReports
  │       └── DraftCard[] [title, last edited, resume link]
  └── Footer
```
*Visible based on role

**States:**
- Loading: Skeleton cards
- Empty: "You haven't submitted any expenses yet. Create your first report."
- Error: Inline alert banner

---

### Screen: Create / Edit Expense Report

**Route:** `/expenses/new` or `/expenses/{report_id}/edit`
**Purpose:** Create or edit an expense report with line items and receipt uploads
**Auth required:** Yes

**Data requirements:**
- Loads (edit): GET /v1/expenses/reports/{report_id}
- Loads: GET /v1/admin/categories (for category dropdown)
- Writes: POST /v1/expenses/reports (create)
- Writes: PATCH /v1/expenses/reports/{report_id} (edit header)
- Writes: POST /v1/expenses/reports/{report_id}/line-items (add item)
- Writes: POST .../line-items/{item_id}/receipt (upload receipt)

**Component hierarchy:**
```
PageLayout
  ├── Header
  ├── MainContent
  │   ├── ReportHeader
  │   │   ├── TitleInput
  │   │   ├── DateRangePicker [start_date, end_date]
  │   │   └── BusinessPurposeTextarea
  │   ├── RejectionBanner* [shown if report was previously rejected, with reason]
  │   ├── LineItemList
  │   │   └── LineItemRow[]
  │   │       ├── DatePicker
  │   │       ├── CategorySelect
  │   │       ├── VendorInput
  │   │       ├── AmountInput + CurrencySelect
  │   │       ├── DescriptionInput
  │   │       ├── ReceiptUpload [file picker, preview thumbnail, OCR status indicator]
  │   │       ├── PolicyViolationBadge* [inline warning/error]
  │   │       └── RemoveButton
  │   ├── AddLineItemButton
  │   ├── TotalSummary [calculated total by currency]
  │   └── ActionBar
  │       ├── SaveDraftButton
  │       ├── SubmitButton
  │       └── CancelButton
  └── Footer
```

**User interactions:**

| Interaction | Trigger | Outcome |
|-------------|---------|---------|
| Add line item | Click "Add Line Item" | Adds empty row to LineItemList |
| Upload receipt | File picker on LineItemRow | POST receipt → shows OCR processing spinner → pre-fills fields |
| Save draft | Click "Save Draft" | POST/PATCH report → toast "Draft saved" |
| Submit | Click "Submit" | POST /submit → validates policy → shows violations or confirms submission |
| Acknowledge duplicate warning | Modal confirmation | Sets acknowledge_warnings=true, resubmits |

---

### Screen: Expense Report Detail (Read-Only)

**Route:** `/expenses/{report_id}`
**Purpose:** View submitted report details, approval history, receipt images
**Auth required:** Yes

**Data requirements:**
- Loads: GET /v1/expenses/reports/{report_id}

**Component hierarchy:**
```
PageLayout
  ├── Header
  ├── MainContent
  │   ├── StatusBanner [current status, submitted date]
  │   ├── ReportHeader [title, date range, purpose — read-only]
  │   ├── LineItemTable
  │   │   └── LineItemRow[] [date, category, vendor, amount, receipt thumbnail]
  │   ├── TotalSummary
  │   └── ApprovalTimeline
  │       └── TimelineEntry[] [actor, action, timestamp, comment]
  └── Footer
```

---

### Screen: Approval Queue

**Route:** `/approvals`
**Purpose:** Manager or Finance reviewer sees reports awaiting their action
**Auth required:** Yes
**Required role:** Manager or Finance Reviewer

**Data requirements:**
- Loads: GET /v1/approvals/pending

**Component hierarchy:**
```
PageLayout
  ├── Header
  ├── MainContent
  │   ├── QueueHeader [pending count, sort controls]
  │   ├── PendingReportList
  │   │   └── PendingReportCard[]
  │   │       ├── SubmitterInfo [name, cost center]
  │   │       ├── ReportSummary [title, total, item count, submitted date]
  │   │       ├── PendingDuration [days pending, urgency badge if >3 days]
  │   │       └── QuickActions [View, Approve, Reject]
  │   └── Pagination
  └── Footer
```

**User interactions:**

| Interaction | Trigger | Outcome |
|-------------|---------|---------|
| View report | Click "View" | Navigate to report detail with approval actions |
| Quick approve | Click "Approve" | Confirmation modal → POST approve → toast + remove from list |
| Quick reject | Click "Reject" | Rejection reason modal → POST reject → toast + remove from list |

---

### Screen: Approval Detail

**Route:** `/approvals/{report_id}`
**Purpose:** Full report view with approve/reject/request-info actions
**Auth required:** Yes
**Required role:** Designated approver

**Component hierarchy:**
```
PageLayout
  ├── Header
  ├── MainContent
  │   ├── ReportDetail [same as read-only detail view]
  │   ├── ReceiptViewer [expandable receipt images]
  │   └── ApprovalActionBar
  │       ├── ApproveButton
  │       ├── RejectButton [opens reason textarea]
  │       └── RequestInfoButton [opens question textarea]
  └── Footer
```

---

### Screen: Manager Dashboard

**Route:** `/dashboard/manager`
**Purpose:** Team spend vs. budget overview
**Auth required:** Yes
**Required role:** Manager

**Data requirements:**
- Loads: GET /v1/reports/manager

**Component hierarchy:**
```
PageLayout
  ├── Header
  ├── MainContent
  │   ├── BudgetSummaryCard [budget, spent, remaining, % used — with progress bar]
  │   ├── PeriodSelector [month picker]
  │   ├── TeamSpendTable
  │   │   └── EmployeeRow[] [name, submitted, approved, pending]
  │   ├── ExportCSVButton
  │   └── PendingApprovalsBanner [link to approval queue if pending > 0]
  └── Footer
```

---

### Screen: Finance Dashboard

**Route:** `/dashboard/finance`
**Purpose:** Organization-wide expense reporting
**Auth required:** Yes
**Required role:** Finance Reviewer or Finance Administrator

**Data requirements:**
- Loads: GET /v1/reports/finance

**Component hierarchy:**
```
PageLayout
  ├── Header
  ├── MainContent
  │   ├── FilterBar [period, cost center, category, status]
  │   ├── SummaryCards [total amount, report count, average amount]
  │   ├── CostCenterBreakdownTable [cost center, total, count]
  │   ├── CategoryBreakdownTable [category, total, count]
  │   ├── StatusBreakdownTable [status, total, count]
  │   └── ExportCSVButton
  └── Footer
```

---

### Screen: Admin Panel

**Route:** `/admin`
**Purpose:** Manage expense categories, per diem rates, approval thresholds
**Auth required:** Yes
**Required role:** Finance Administrator

**Data requirements:**
- Loads: GET /v1/admin/categories
- Loads: GET /v1/admin/approval-thresholds

**Component hierarchy:**
```
PageLayout
  ├── Header
  ├── MainContent
  │   ├── TabBar [Categories, Thresholds]
  │   ├── CategoriesTab
  │   │   ├── CategoryTable
  │   │   │   └── CategoryRow[] [name, daily limit, reimbursable toggle, per diem rates, edit button]
  │   │   └── AddCategoryButton
  │   └── ThresholdsTab
  │       ├── FinanceReviewThresholdInput [$500]
  │       ├── AutoEscalationDaysInput [5]
  │       ├── ReminderDaysInput [3]
  │       └── SaveButton
  └── Footer
```

---

## Navigation & Routing

```
/                           → Employee Dashboard
/login                      → SSO Login redirect
/expenses/new               → Create Expense Report
/expenses/{id}              → View Expense Report (read-only)
/expenses/{id}/edit         → Edit Expense Report (draft/rejected only)
/approvals                  → Approval Queue (Manager / Finance)
/approvals/{id}             → Approval Detail with actions
/dashboard/manager          → Manager Team Spend Dashboard
/dashboard/finance          → Finance Reporting Dashboard
/admin                      → Admin Panel (Finance Administrator)
```

Role-based navigation visibility:

| Route | Employee | Manager | Finance Reviewer | Finance Admin |
|-------|----------|---------|-----------------|---------------|
| / | ✅ | ✅ | ✅ | ✅ |
| /expenses/* | ✅ | ✅ | ✅ | ✅ |
| /approvals/* | ❌ | ✅ | ✅ | ✅ |
| /dashboard/manager | ❌ | ✅ | ❌ | ❌ |
| /dashboard/finance | ❌ | ❌ | ✅ | ✅ |
| /admin | ❌ | ❌ | ❌ | ✅ |

---

## Error Handling Patterns

**Inline field validation:** Show error below field on blur (required fields, format, range)
**Form-level errors:** Banner at top of form after failed submission (policy violations)
**Toast notifications:** Success (report saved, approved) and non-blocking errors (OCR failed — enter manually)
**Full-page errors:** 404 (report not found), 403 (forbidden — "You don't have access to this report"), 500 (unexpected — "Something went wrong, please try again")
**Policy violations:** Inline badges on line items with specific violation messages (FR-005)
