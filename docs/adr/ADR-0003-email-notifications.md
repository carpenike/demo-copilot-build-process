# ADR-0003: Email Notification Service

> **Status:** Accepted
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering
> **Project:** example-ticket-app

---

## Context

The system must send email notifications on ticket status changes (FR-012) and
when customers comment on assigned tickets (FR-013). The stakeholder specified
SendGrid as the email provider. Emails should not block the API response — they
should be dispatched asynchronously.

---

## Decision

> We will use **Celery + Redis** for async task processing and the **SendGrid
> API** (via `sendgrid` Python SDK) for email delivery.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Background tasks | Celery + Redis | Celery + Redis | ✅ |
| Secrets | AWS Secrets Manager | SendGrid API key via Secrets Manager | ✅ |
| Infrastructure | Terraform + internal modules | ElastiCache Redis via Terraform | ✅ |

---

## Options Considered

### Option 1: Celery + Redis + SendGrid ← Chosen

**Pros:**
- Approved stack for background tasks per enterprise standards
- Async dispatch keeps API response times low
- Celery provides retry, dead-letter, and monitoring out of the box
- SendGrid SDK is well-maintained and simple to integrate

**Cons:**
- Redis is an additional infrastructure component
- Celery adds operational surface area

---

### Option 2: Synchronous email in request handler

**Pros:**
- Simpler — no additional infrastructure

**Cons:**
- Blocks API response on email delivery (100–500ms per email)
- If SendGrid is down, API requests fail
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
- Redis connection via ElastiCache, credentials in Secrets Manager
- SendGrid API key stored in AWS Secrets Manager, loaded via config
- Use Celery `autoretry_for` with exponential backoff for transient failures

---

## References
- FR-012, FR-013 (notification requirements)
- Related: ADR-0001 (language), ADR-0002 (data storage)
