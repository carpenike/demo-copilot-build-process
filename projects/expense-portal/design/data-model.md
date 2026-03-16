# Data Model: Employee Expense Management Portal

> **Version:** 1.0
> **Date:** 2026-03-13
> **Produced by:** Design Agent
> **Related ADRs:** ADR-0002 (data storage), ADR-0004 (authentication), ADR-0005 (blob storage)

---

## Overview

All relational data is stored in Azure Database for PostgreSQL — Flexible Server (ADR-0005). Receipt files are stored in Azure Blob Storage. The data model supports:

- Expense report creation and lifecycle management
- Multi-level approval workflow with immutable audit trail
- Configurable policy engine (categories, per diem rates, thresholds)
- Workday-synced employee/manager/cost center hierarchy
- SOX compliance: append-only audit logs, soft deletes, no post-approval mutation

---

## Entity Relationship Diagram

```mermaid
erDiagram
    EMPLOYEE ||--o{ EXPENSE_REPORT : submits
    EMPLOYEE ||--o{ APPROVAL_ACTION : performs
    EMPLOYEE }o--|| EMPLOYEE : "reports_to (manager)"
    EMPLOYEE }o--|| COST_CENTER : "belongs_to"

    EXPENSE_REPORT ||--|{ LINE_ITEM : contains
    EXPENSE_REPORT ||--o{ APPROVAL_ACTION : "has audit trail"
    EXPENSE_REPORT ||--o{ ACTION_TOKEN : "has email tokens"

    LINE_ITEM ||--o| RECEIPT : "has attachment"
    LINE_ITEM }o--|| EXPENSE_CATEGORY : "categorized_as"
    LINE_ITEM ||--o{ POLICY_VIOLATION : "flagged_with"

    EXPENSE_CATEGORY ||--o{ PER_DIEM_RATE : "has rates"

    APPROVAL_THRESHOLD ||--|| APPROVAL_THRESHOLD : "singleton config"

    EMPLOYEE {
        uuid id PK
        string entra_oid UK "Microsoft Entra ID Object ID"
        string email UK
        string full_name
        uuid manager_id FK "self-reference"
        uuid cost_center_id FK
        string role "employee | finance_reviewer | finance_admin"
        boolean is_active
        timestamp workday_synced_at
        timestamp created_at
        timestamp updated_at
    }

    COST_CENTER {
        uuid id PK
        string code UK "e.g. CC-ENG-001"
        string name
        decimal budget_amount "current period budget"
        string budget_period "e.g. 2026-03"
        string workday_id UK
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    EXPENSE_REPORT {
        uuid id PK
        string report_number UK "auto-generated RPT-NNNN"
        uuid submitter_id FK
        string title
        date start_date
        date end_date
        string business_purpose
        string status "draft|submitted|manager_approved|finance_review|approved|rejected|information_requested|payment_processing|paid|cancelled"
        decimal total_amount "calculated"
        string currency "USD|CAD"
        uuid current_approver_id FK "nullable"
        timestamp submitted_at
        timestamp approved_at
        timestamp rejected_at
        boolean is_deleted "soft delete"
        timestamp created_at
        timestamp updated_at
    }

    LINE_ITEM {
        uuid id PK
        uuid report_id FK
        date expense_date
        uuid category_id FK
        string vendor_name
        decimal amount
        string currency "USD|CAD"
        string description
        uuid receipt_id FK "nullable"
        string ocr_status "null|processing|completed|failed"
        integer sort_order
        timestamp created_at
        timestamp updated_at
    }

    RECEIPT {
        uuid id PK
        uuid line_item_id FK
        string blob_path "Azure Blob Storage path"
        string original_filename
        string content_type "image/jpeg|image/png|application/pdf"
        integer file_size_bytes
        string ocr_task_id "Celery task ID"
        jsonb ocr_results "extracted fields with confidence scores"
        timestamp created_at
    }

    EXPENSE_CATEGORY {
        uuid id PK
        string name UK
        decimal daily_limit "nullable — null means no limit"
        boolean is_reimbursable
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    PER_DIEM_RATE {
        uuid id PK
        uuid category_id FK
        string destination "e.g. US-Domestic, US-NYC, CA-Domestic"
        decimal rate
        timestamp effective_from
        timestamp effective_to "nullable — null means current"
        timestamp created_at
        timestamp updated_at
    }

    APPROVAL_ACTION {
        uuid id PK
        uuid report_id FK
        uuid actor_id FK
        string action "submitted|manager_approved|finance_approved|rejected|information_requested|escalated|resubmitted"
        string comment "nullable"
        inet ip_address
        timestamp created_at
    }

    ACTION_TOKEN {
        uuid id PK
        uuid report_id FK
        uuid approver_id FK
        string token UK "cryptographically random, 256-bit"
        string intended_action "approve|reject|request_info"
        boolean is_used
        timestamp expires_at
        timestamp used_at "nullable"
        timestamp created_at
    }

    APPROVAL_THRESHOLD {
        uuid id PK
        decimal finance_review_threshold "default 500.00"
        integer auto_escalation_business_days "default 5"
        integer reminder_business_days "default 3"
        timestamp updated_at
        uuid updated_by FK
    }

    NOTIFICATION {
        uuid id PK
        uuid recipient_id FK
        uuid report_id FK "nullable"
        string channel "email|in_app"
        string event_type "submitted|approved|rejected|info_requested|reminder|escalated"
        string subject
        text body
        boolean is_read "for in_app notifications"
        timestamp sent_at
        timestamp read_at "nullable"
        timestamp created_at
    }

    WORKDAY_SYNC_LOG {
        uuid id PK
        timestamp started_at
        timestamp completed_at
        string status "success|partial|failed"
        integer employees_updated
        integer cost_centers_updated
        integer errors
        text error_details "nullable"
    }
```

---

## Entity Descriptions

### EMPLOYEE
Represents a user of the system. Synced nightly from Workday (FR-016). The `entra_oid` is the unique identifier from Microsoft Entra ID used for authentication matching (ADR-0006). The `role` field determines application-level permissions. Manager relationship is a self-referencing foreign key derived from Workday hierarchy.

**Indexes:**
- `entra_oid` — unique, used for login lookup
- `email` — unique
- `manager_id` — for approval routing and manager dashboard queries
- `cost_center_id` — for reporting aggregation

### COST_CENTER
Organizational cost center from Workday. Budget amounts are maintained per period for the manager dashboard (FR-020).

### EXPENSE_REPORT
The core entity. Tracks the full lifecycle from draft through payment. The `status` field is the state machine driver for the approval workflow.

**State machine:**
```mermaid
stateDiagram-v2
    [*] --> draft : Create
    draft --> submitted : Submit
    draft --> cancelled : Delete draft
    submitted --> manager_approved : Manager approves
    submitted --> rejected : Manager rejects
    submitted --> information_requested : Manager requests info
    submitted --> submitted : Escalated to manager's manager
    information_requested --> submitted : Employee resubmits
    manager_approved --> finance_review : Line item > threshold
    manager_approved --> approved : All items <= threshold
    finance_review --> approved : Finance approves
    finance_review --> rejected : Finance rejects
    approved --> payment_processing : SAP batch generated
    payment_processing --> paid : SAP confirms payment
    rejected --> draft : Employee edits for resubmission
    rejected --> submitted : Employee resubmits
```

**Indexes:**
- `submitter_id, status` — for employee dashboard (own reports filtered by status)
- `current_approver_id, status` — for approval queue (pending reports for a specific approver)
- `submitted_at` — for reporting date range queries
- `status` — for finance dashboard filtering

**Constraints:**
- `CHECK (end_date >= start_date)`
- `CHECK (status IN ('draft','submitted','manager_approved','finance_review','approved','rejected','information_requested','payment_processing','paid','cancelled'))`

### LINE_ITEM
Individual expense entries within a report. Each line item has an optional receipt attachment and is validated against the policy engine at submission time.

**Indexes:**
- `report_id, sort_order` — for ordered retrieval within a report
- `(submitter via report).id, expense_date, amount, vendor_name` — for duplicate detection (FR-007)

### RECEIPT
Metadata for receipt files stored in Azure Blob Storage. The `blob_path` references the file in Blob Storage; the actual file is never stored in PostgreSQL. OCR results are stored as JSONB for flexible schema.

### EXPENSE_CATEGORY
Admin-configurable expense categories (FR-024). The `daily_limit` is enforced by the policy engine at submission time.

### PER_DIEM_RATE
Destination-specific per diem rates per category (FR-014). Supports temporal validity (`effective_from`/`effective_to`) so rate changes don't retroactively affect existing reports.

### APPROVAL_ACTION
**Append-only audit trail** (NFR-011, NFR-015). No UPDATE or DELETE operations are permitted on this table. Every state change on an expense report creates a new row. Captures actor, action, timestamp, IP address, and optional comment.

**Database enforcement:**
- No UPDATE/DELETE triggers (or revoke UPDATE/DELETE from application role)
- `created_at` set by database default, not application code

**Retention:** 7 years per NFR-011 and NFR-014.

### ACTION_TOKEN
Single-use, time-bounded tokens for email approval action links (ADR-0006, GF-007). Tokens are cryptographically random, expire after 30 minutes, and are marked used after first use to prevent replay.

### APPROVAL_THRESHOLD
Singleton configuration table for system-wide approval settings. Managed by Finance Administrators via the admin panel (FR-024).

### NOTIFICATION
Tracks both email and in-app notifications. In-app notifications support read/unread state for the notification indicator in the UI.

### WORKDAY_SYNC_LOG
Operational logging for the nightly Workday sync job. Used for monitoring and troubleshooting sync failures.

---

## Data Flow Diagrams

### Expense Submission Flow

```mermaid
flowchart TD
    A[Employee] -->|Creates report + line items| B[FastAPI]
    B -->|Saves draft| C[(PostgreSQL)]
    A -->|Uploads receipt| B
    B -->|Stores file| D[Azure Blob Storage]
    B -->|Queues OCR task| E[Redis]
    E -->|Processes| F[Celery Worker]
    F -->|Calls| G[Azure Document Intelligence]
    G -->|Returns extracted fields| F
    F -->|Updates line item with OCR results| C
    A -->|Submits report| B
    B -->|Validates policy| C
    B -->|Checks duplicates| C
    B -->|Creates approval_action record| C
    B -->|Sets current_approver| C
    B -->|Queues notification| E
```

### Approval Flow

```mermaid
flowchart TD
    A[Manager/Finance] -->|Views pending approvals| B[FastAPI]
    B -->|Queries by current_approver_id| C[(PostgreSQL)]
    A -->|Approves/Rejects| B
    B -->|Creates approval_action record| C
    B -->|Updates report status| C
    B -->|Queues notification| D[Redis]

    E[Celery Beat] -->|Scheduled: check stale approvals| F[Celery Worker]
    F -->|Queries reports pending > 5 days| C
    F -->|Escalates: updates current_approver| C
    F -->|Creates escalation approval_action| C
    F -->|Queues notification| D
```

### Integration Flow

```mermaid
flowchart TD
    A[Celery Beat] -->|Nightly 02:00 UTC| B[Celery Worker]
    B -->|GET /employees, /managers, /cost-centers| C[Workday API]
    C -->|Employee + hierarchy data| B
    B -->|Upserts employees, cost_centers| D[(PostgreSQL)]
    B -->|Logs sync results| D

    E[Report approved] -->|Queues SAP task| F[Redis]
    F -->|Processes| G[Celery Worker]
    G -->|Generates IDoc batch| H[SAP S/4HANA]
    G -->|Writes GL journal entry| H
    G -->|Updates report status to payment_processing| D
```

---

## Storage Strategy

| Data Type | Storage | Encryption | Retention |
|-----------|---------|------------|-----------|
| Relational data (reports, line items, employees) | PostgreSQL | TDE (AES-256, platform-managed key) | Active data: indefinite; soft-deleted: 7 years |
| Audit trail (approval_actions) | PostgreSQL | TDE (AES-256) | 7 years (NFR-011) — append-only, no purge |
| Receipt images | Azure Blob Storage | SSE (AES-256) | 7 years (NFR-014) — immutable WORM policy |
| Receipt images > 90 days | Azure Blob Storage Cool tier | SSE (AES-256) | Auto-tiered via lifecycle policy |
| Celery task results | PostgreSQL | TDE (AES-256) | 30 days TTL |
| Session data | Redis | In-transit TLS, at-rest encryption | Session TTL (24 hours) |
