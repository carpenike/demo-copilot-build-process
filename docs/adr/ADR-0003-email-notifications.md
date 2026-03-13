# ADR-0003: Email Notification Service

> **Status:** Accepted
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering
> **Project:** example-ticket-app

---

## Context

The system must send email notifications on ticket status changes (FR-012) and
when customers comment on assigned tickets (FR-013). The stakeholder specified
Azure Communication Services as the email provider. Emails should not block the API response — they
should be dispatched asynchronously.

---

## Decision

> We will use **Celery + Redis** for async task processing and the **Azure
> Communication Services Email API** (via `azure-communication-email` Python SDK) for email delivery.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Background tasks | Celery + Redis | Celery + Redis | ✅ |
| Secrets | Azure Key Vault | Email API key via Key Vault | ✅ |
| Infrastructure | Terraform + internal modules | Azure Cache for Redis via Terraform | ✅ |

---

## Options Considered

### Option 1: Celery + Redis + Azure Communication Services ← Chosen

**Pros:**
- Approved stack for background tasks per enterprise standards
- Async dispatch keeps API response times low
- Celery provides retry, dead-letter, and monitoring out of the box
- Azure Communication Services SDK is well-maintained and simple to integrate

**Cons:**
- Redis is an additional infrastructure component
- Celery adds operational surface area

---

### Option 2: Synchronous email in request handler

**Pros:**
- Simpler — no additional infrastructure

**Cons:**
- Blocks API response on email delivery (100–500ms per email)
- If email provider is down, API requests fail
- Violates NFR-001 (200ms response time)

---

## Consequences

### Positive
- Email dispatch does not impact API latency
- Failed emails are retried automatically
- Clear separation of concerns (API ↔ workers)

### Negative / Trade-offs
- Redis + Celery workers are additional components to deploy and monitor

### Risks
- **Risk:** Email delivery delay if Celery queue backs up
  - **Mitigation:** HPA on Celery workers, monitor queue depth via Prometheus

---

## Implementation Notes

- Celery task: `send_status_notification(ticket_id, old_status, new_status)`
- Celery task: `send_comment_notification(ticket_id, comment_id)`
- Redis connection via Azure Cache for Redis, credentials in Key Vault
- Azure Communication Services connection string stored in Azure Key Vault, loaded via config
- Use Celery `autoretry_for` with exponential backoff for transient failures

---

## References
- FR-012, FR-013 (notification requirements)
- Related: ADR-0001 (language), ADR-0002 (data storage)
