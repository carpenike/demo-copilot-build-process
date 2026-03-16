# Architecture Overview: Employee Expense Management Portal

> **Version:** 1.0
> **Date:** 2026-03-13
> **Produced by:** Design Agent
> **Project:** expense-portal (FIN-EXP-2026)
> **Related ADRs:** ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0006

---

## System Context Diagram

```mermaid
C4Context
    title System Context — Employee Expense Management Portal

    Person(employee, "Employee", "Submits expense reports, uploads receipts")
    Person(manager, "Cost Center Manager", "Approves/rejects direct reports' expenses")
    Person(finance, "Finance Team", "Reviews high-value reports, runs dashboards, configures policy")

    System(portal, "Expense Management Portal", "Web application for expense submission, approval, policy enforcement, and reporting")

    System_Ext(entra, "Microsoft Entra ID", "Corporate SSO identity provider")
    System_Ext(workday, "Workday", "HR system — employee, manager hierarchy, cost center data")
    System_Ext(sap, "SAP S/4HANA", "ERP — GL coding, payment batch processing via IDoc")
    System_Ext(docai, "Azure AI Document Intelligence", "OCR receipt extraction service")
    System_Ext(email, "Corporate Email (SMTP)", "Transactional email notifications")

    Rel(employee, portal, "Submits expenses, uploads receipts", "HTTPS")
    Rel(manager, portal, "Reviews and approves expenses", "HTTPS / Email links")
    Rel(finance, portal, "Reviews reports, manages policy, exports data", "HTTPS")

    Rel(portal, entra, "Authenticates users", "OIDC / OAuth2")
    Rel(portal, workday, "Syncs employee hierarchy nightly", "REST API")
    Rel(portal, sap, "Sends payment batches, GL entries", "IDoc / RFC")
    Rel(portal, docai, "Extracts receipt data", "REST API")
    Rel(portal, email, "Sends notifications", "SMTP / STARTTLS")
```

---

## Component Diagram

```mermaid
C4Container
    title Container Diagram — Expense Management Portal

    Person(user, "User", "Employee / Manager / Finance")

    System_Boundary(azure, "Azure / AKS Cluster") {
        Container(apim, "Azure API Management", "API Gateway", "TLS termination, rate limiting, routing")
        Container(api, "Expense API", "Python / FastAPI", "REST API + Jinja2 SSR frontend. Handles auth, CRUD, policy validation, reporting.")
        Container(worker_ocr, "OCR Worker", "Python / Celery", "Processes receipt images via Azure Document Intelligence")
        Container(worker_notify, "Notification Worker", "Python / Celery", "Sends email and in-app notifications")
        Container(worker_integ, "Integration Worker", "Python / Celery", "SAP IDoc generation, GL journal entries")
        Container(worker_sched, "Scheduled Worker", "Python / Celery Beat", "Workday sync, approval escalation, reminders")
        ContainerDb(pg, "PostgreSQL", "Azure DB for PostgreSQL Flexible Server", "Reports, line items, employees, audit logs, policy config")
        ContainerDb(redis, "Redis", "Azure Cache for Redis", "Celery message broker, session store")
        ContainerDb(blob, "Blob Storage", "Azure Blob Storage", "Receipt images (WORM, 7-year retention)")
    }

    System_Ext(entra, "Microsoft Entra ID", "OIDC SSO")
    System_Ext(workday, "Workday API", "HR data")
    System_Ext(sap, "SAP S/4HANA", "ERP")
    System_Ext(docai, "Azure AI Document Intelligence", "OCR")
    System_Ext(smtp, "SMTP Relay", "Email")

    Rel(user, apim, "HTTPS requests", "TLS 1.2+")
    Rel(apim, api, "Proxies requests", "HTTP internal")
    Rel(api, pg, "Reads/writes", "asyncpg / TLS")
    Rel(api, redis, "Enqueues tasks, sessions", "TLS")
    Rel(api, blob, "Uploads receipts", "Azure SDK / TLS")
    Rel(api, entra, "OIDC auth flow", "HTTPS")

    Rel(worker_ocr, redis, "Consumes tasks", "TLS")
    Rel(worker_ocr, docai, "Calls OCR API", "HTTPS")
    Rel(worker_ocr, pg, "Updates OCR results", "TLS")
    Rel(worker_ocr, blob, "Reads receipt images", "TLS")

    Rel(worker_notify, redis, "Consumes tasks", "TLS")
    Rel(worker_notify, smtp, "Sends email", "STARTTLS")
    Rel(worker_notify, pg, "Creates notification records", "TLS")

    Rel(worker_integ, redis, "Consumes tasks", "TLS")
    Rel(worker_integ, sap, "Sends IDoc / GL entries", "RFC / TLS")
    Rel(worker_integ, pg, "Reads report data, updates status", "TLS")

    Rel(worker_sched, redis, "Publishes scheduled tasks", "TLS")
    Rel(worker_sched, workday, "Syncs employee data", "HTTPS")
    Rel(worker_sched, pg, "Reads/writes sync + escalation data", "TLS")
```

---

## Deployment Architecture

```mermaid
flowchart TB
    subgraph Internet
        User[Browser / Mobile]
    end

    subgraph Azure["Azure Subscription"]
        subgraph APIM["Azure API Management"]
            GW[API Gateway]
        end

        subgraph AKS["AKS Cluster"]
            subgraph ns["namespace: expense-portal"]
                API["expense-api<br/>Deployment (3 replicas)<br/>HPA: 3–10"]
                WO["ocr-worker<br/>Deployment (2 replicas)<br/>HPA: 2–5"]
                WN["notify-worker<br/>Deployment (1 replica)<br/>HPA: 1–3"]
                WI["integration-worker<br/>Deployment (1 replica)"]
                WS["scheduled-worker<br/>Deployment (1 replica)<br/>Celery Beat"]
            end
        end

        PG["Azure DB for PostgreSQL<br/>Flexible Server<br/>Zone-redundant HA"]
        REDIS["Azure Cache for Redis<br/>Standard C1<br/>Zone-redundant"]
        BLOB["Azure Blob Storage<br/>GPv2, LRS<br/>Immutable policy"]
        KV["Azure Key Vault<br/>Secrets + certificates"]
        MON["Azure Monitor<br/>+ Application Insights<br/>+ Managed Prometheus"]
        DOCAI["Azure AI<br/>Document Intelligence"]
    end

    subgraph External["External Systems"]
        ENTRA["Microsoft Entra ID"]
        WORKDAY["Workday"]
        SAP["SAP S/4HANA"]
        SMTP["SMTP Relay"]
    end

    User -->|HTTPS| GW
    GW -->|HTTP internal| API
    API --- PG
    API --- REDIS
    API --- BLOB
    API -->|OIDC| ENTRA
    WO --- REDIS
    WO --- DOCAI
    WO --- PG
    WO --- BLOB
    WN --- REDIS
    WN --- SMTP
    WN --- PG
    WI --- REDIS
    WI --- SAP
    WI --- PG
    WS --- REDIS
    WS --- WORKDAY
    WS --- PG
    KV -.->|CSI secrets driver| AKS
    AKS -.->|logs, metrics, traces| MON
```

---

## Component Responsibilities

### Expense API (FastAPI)
- **Auth:** OIDC login/callback/logout, session management, RBAC middleware
- **Expense CRUD:** Create/read/update reports and line items, draft management
- **Submission:** Policy validation, duplicate detection, approval routing
- **Approvals:** Approve/reject/request-info endpoints, email action token validation
- **Dashboards:** Finance and manager reporting queries, CSV export
- **Admin:** Category, per diem, and threshold management
- **Frontend:** Server-rendered Jinja2 templates with HTMX for interactivity
- **Operational:** `/health`, `/ready`, `/metrics` endpoints

### OCR Worker (Celery)
- Consumes receipt upload tasks from the `ocr` queue
- Downloads receipt from Blob Storage → calls Azure Document Intelligence → extracts fields with confidence scores → updates line item in PostgreSQL
- Retries with exponential backoff on transient failures

### Notification Worker (Celery)
- Consumes notification tasks from the `notifications` queue
- Sends transactional email via SMTP relay
- Creates in-app notification records in PostgreSQL
- Generates single-use action tokens for email approval links

### Integration Worker (Celery)
- Consumes from the `integrations` queue
- Generates SAP IDoc payment batch files from approved reports
- Writes GL journal entry records to SAP
- Updates report status to `payment_processing`
- Retries with backoff on SAP unavailability; queues for manual review after max retries

### Scheduled Worker (Celery Beat)
- `sync_workday` (daily 02:00 UTC): syncs employees, managers, cost centers from Workday API
- `check_stale_approvals` (daily 08:00 UTC): escalates reports pending > 5 business days
- `send_approval_reminders` (daily 08:00 UTC): reminds approvers of reports pending > 3 business days

---

## Cross-Cutting Concerns

### Security
| Concern | Implementation |
|---------|---------------|
| Authentication | Microsoft Entra ID OIDC (ADR-0006) |
| Authorization | Application-level RBAC with Workday-derived hierarchy |
| Secrets | Azure Key Vault → AKS CSI secrets driver |
| TLS | 1.2+ everywhere — APIM terminates external TLS; internal uses service mesh mTLS |
| Email action links | Single-use, 30-minute expiry, SSO required before action execution |
| CSRF | SameSite=Lax cookies + CSRF tokens on state-changing Jinja2 forms |
| Input validation | Pydantic models validate all API input; parameterized SQL queries (SQLAlchemy) |

### Observability
| Signal | Implementation | Destination |
|--------|---------------|-------------|
| Logs | structlog → stdout (JSON format) | Azure Monitor Logs |
| Metrics | prometheus-fastapi-instrumentator + Celery Prometheus exporter | Azure Monitor managed Prometheus |
| Traces | OpenTelemetry SDK (azure-monitor-opentelemetry) | Application Insights |
| Health | `/health` (liveness), `/ready` (readiness with DB + Redis checks) | AKS kubelet probes |

### Resilience
| Failure Scenario | Handling |
|------------------|----------|
| PostgreSQL unavailable | `/ready` returns 503 → AKS stops routing traffic; API returns 503 to user |
| Redis unavailable | `/ready` returns 503; tasks queue in API memory briefly, processed when Redis recovers |
| Azure Document Intelligence unavailable | OCR task retries with backoff; receipt upload succeeds, OCR pre-fill skipped; user enters fields manually |
| SAP unavailable | Integration task retries with backoff; report stays in `approved` status; alert sent to ops |
| Workday API unavailable | Sync retries 3x with backoff; previous day's data remains; alert sent to ops |
| SMTP unavailable | Notification task retries; in-app notification still created in DB |

---

## Network Architecture

```
Internet → Azure API Management (public IP, TLS termination, WAF)
         → AKS Ingress Controller (internal)
         → expense-api Service (ClusterIP)

All backend services (PostgreSQL, Redis, Blob, Key Vault, Document Intelligence)
accessed via Azure Private Endpoints within the AKS VNet.

No direct public access to any backend service.
```

---

## Scaling Strategy

| Component | Min Replicas | Max Replicas | Scale Trigger |
|-----------|-------------|-------------|---------------|
| expense-api | 3 | 10 | CPU > 70% or request latency p95 > 1.5s |
| ocr-worker | 2 | 5 | Queue depth > 10 |
| notify-worker | 1 | 3 | Queue depth > 50 |
| integration-worker | 1 | 1 | Not scaled — SAP has rate limits |
| scheduled-worker | 1 | 1 | Singleton — Celery Beat leader election |

Target capacity: 1,500 concurrent users (NFR-013) with 3x headroom via HPA scaling.

---

## Quality Checklist

- [x] Every functional requirement (FR-001–FR-024) maps to a specific component
- [x] All technology choices are permitted by enterprise-standards.md
- [x] Every ADR documents alternatives considered and rejection reasons
- [x] API endpoints in wireframe-spec are complete enough to generate test cases
- [x] Data model covers all entities implied by the requirements
- [x] Observability requirements (NFR-016–NFR-019) addressed in architecture
- [x] Security requirements (NFR-007–NFR-012) addressed with specific implementations
- [x] Compliance requirements (NFR-014–NFR-015) supported by data model design
