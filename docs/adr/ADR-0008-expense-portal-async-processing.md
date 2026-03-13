# ADR-0008: Asynchronous Processing & Background Jobs

> **Status:** Proposed
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering, Finance Systems Team
> **Project:** expense-portal (FIN-EXP-2026)

---

## Context

Several operations in the Expense Portal cannot complete synchronously within the 2-second page load target (NFR-001):

1. **OCR processing** — Azure Document Intelligence calls take up to 10 seconds (NFR-002)
2. **SAP IDoc batch generation** — batches of up to 1,000 line items, must complete within 60 seconds (NFR-003)
3. **Workday sync** — nightly synchronization of employee/manager/cost center data (FR-016)
4. **Email notifications** — transactional emails for submission, approval, rejection events (FR-022)
5. **Approval escalation** — scheduled job checking for stale approvals after 5 business days (FR-011)
6. **Approval reminders** — scheduled notification for reports pending 3+ business days (FR-023)

Related requirements: FR-011, FR-016, FR-017, FR-022, FR-023, NFR-001, NFR-002, NFR-003.

---

## Decision

> We will use **Celery with Redis as the message broker** for asynchronous task processing and scheduled jobs because Celery is the approved background task framework per enterprise standards, and Redis is the approved broker.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Background tasks | Celery + Redis | Celery + Redis | ✅ |
| Infrastructure | AKS | Celery workers as AKS deployments; Azure Cache for Redis | ✅ |
| Secrets | Azure Key Vault | Redis connection string in Key Vault | ✅ |
| Language | Python | Celery is Python-native | ✅ |

---

## Options Considered

### Option 1: Celery + Redis ← Chosen

**Description:** Celery task queue with Azure Cache for Redis as the message broker. Celery Beat for scheduled/periodic tasks. Workers deployed as separate AKS pods.

**Pros:**
- Approved by enterprise standards — no exception needed
- Mature, well-documented, widely used in Python ecosystem
- Celery Beat provides cron-like scheduling for Workday sync, escalation checks, and reminders
- Task retry with exponential backoff built in — critical for external service integrations (OCR, SAP, email)
- Workers scale independently from the API via AKS HPA
- Result backend (Redis or PostgreSQL) allows the API to check task status for polling

**Cons:**
- Redis adds an infrastructure dependency (mitigated by Azure Cache for Redis — managed service)
- Celery's monitoring requires Flower or custom metrics exporter

---

### Option 2: Azure Service Bus + custom workers

**Description:** Use Azure Service Bus as the message queue with custom Python consumers deployed as AKS pods.

**Pros:**
- Azure-native, enterprise-grade messaging with dead-letter queues
- Stronger delivery guarantees than Redis (at-least-once with sessions)

**Cons:**
- Not the enterprise-approved pattern (Celery + Redis is explicitly listed)
- Requires custom task dispatch, retry logic, and scheduling — reimplements what Celery provides
- Higher development effort for no meaningful benefit at this scale

---

### Option 3: Async within the API process (FastAPI background tasks)

**Description:** Use FastAPI's `BackgroundTasks` for fire-and-forget operations.

**Pros:**
- No additional infrastructure
- Simple for trivial tasks

**Cons:**
- Tasks die if the API pod restarts — no persistence or retry
- No scheduling capability (can't run Workday nightly sync or escalation checks)
- Cannot scale workers independently from API pods
- Unsuitable for long-running tasks (SAP batch generation at 60 seconds)

---

## Consequences

### Positive
- Well-understood task model: the API enqueues work, dedicated workers process it
- Workers scale independently — OCR bursts and SAP batch runs don't impact API latency
- Built-in retry with backoff for resilient external service integration
- Celery Beat eliminates the need for external cron or Azure Functions for scheduled jobs

### Negative / Trade-offs
- Redis is an additional managed service to operate (Azure Cache for Redis mitigates most ops burden)
- Celery worker pods consume cluster resources even at idle — mitigated by HPA scaling to minimum replicas

### Risks
- Redis unavailability blocks all async processing. **Mitigation:** Azure Cache for Redis with zone redundancy; API continues to accept submissions (tasks queue in memory briefly with Celery's `retry` behavior), and workers recover when Redis returns.
- Task queue backlog during large Workday sync. **Mitigation:** Use dedicated Celery queues — separate queues for `ocr`, `notifications`, `integrations`, `scheduled` — so a backlog in one doesn't starve others.

---

## Implementation Notes

### Task Queues

| Queue | Tasks | Workers | Schedule |
|-------|-------|---------|----------|
| `ocr` | Receipt OCR processing | 2 replicas (HPA: 2–5) | On demand (triggered by upload) |
| `notifications` | Email + in-app notifications | 1 replica (HPA: 1–3) | On demand (triggered by workflow events) |
| `integrations` | SAP IDoc batch, GL journal entries | 1 replica | On demand (triggered by final approval) |
| `scheduled` | Workday sync, escalation check, approval reminders | 1 replica | Cron via Celery Beat |

### Celery Beat Schedule

| Task | Schedule | Description |
|------|----------|-------------|
| `sync_workday` | Daily 02:00 UTC | Nightly employee/hierarchy/cost center sync |
| `check_stale_approvals` | Daily 08:00 UTC | Escalate reports pending > 5 business days |
| `send_approval_reminders` | Daily 08:00 UTC | Remind approvers of reports pending > 3 business days |

### Infrastructure
- **Broker:** Azure Cache for Redis (Standard C1, zone-redundant)
- **Result backend:** PostgreSQL (reuse existing DB — task results stored in `celery_task_results` table)
- **Workers:** Separate AKS Deployment per queue, same Docker image with different entrypoint
- **Monitoring:** Celery Prometheus exporter sidecar for `/metrics` (task duration, queue depth, failure rate)

---

## References
- [Celery documentation](https://docs.celeryq.dev/)
- [Azure Cache for Redis](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/)
- Related ADRs: ADR-0004 (language), ADR-0005 (data storage), ADR-0007 (OCR)
- Related requirements: FR-011, FR-016, FR-017, FR-022, FR-023, NFR-001–NFR-003
