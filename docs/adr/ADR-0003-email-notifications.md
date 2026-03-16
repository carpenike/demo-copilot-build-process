# ADR-0003: Platform Async Processing and Email Delivery

> **Status:** Accepted
> **Date:** 2026-03-13
> **Deciders:** Platform Engineering
> **Scope:** All projects

---

## Context

Multiple services require asynchronous background processing — email notifications,
report generation, data sync jobs, and other tasks that should not block API
responses. This ADR establishes the standard async processing stack and email
delivery mechanism for all Python services on the platform.

The enterprise standards (`governance/enterprise-standards.md`) specify
**Celery + Redis** as the approved background task framework.

---

## Decision

> Python services requiring async processing MUST use **Celery + Redis** for
> task queues. Email delivery MUST use the **Azure Communication Services
> Email API** via the `azure-communication-email` Python SDK.

---

## Governance Compliance

| Constraint | Standard | This Decision | Compliant? |
|------------|----------|---------------|------------|
| Background tasks | Celery + Redis | Celery + Redis | ✅ |
| Secrets | Azure Key Vault | Email API key via Key Vault | ✅ |
| Infrastructure | Terraform + internal modules | Azure Cache for Redis via Terraform | ✅ |

---

## Options Considered

### Option 1: Celery + Redis + Azure Communication Services ← Standard

**Pros:**
- Approved stack for background tasks per enterprise standards
- Async dispatch keeps API response times low across all services
- Celery provides retry, dead-letter, and monitoring out of the box
- Azure Communication Services SDK is well-maintained and simple to integrate
- Consistent operational model — same monitoring and alerting patterns everywhere

**Cons:**
- Redis is an additional infrastructure component per service
- Celery adds operational surface area

---

### Option 2: Synchronous email in request handler

**Pros:**
- Simpler — no additional infrastructure

**Cons:**
- Blocks API response on email delivery (100–500ms per email)
- If email provider is down, API requests fail
- Violates typical latency NFRs
- Not scalable across multiple services

---

## Consequences

### Positive
- Email and background task dispatch does not impact API latency for any service
- Failed tasks are retried automatically with exponential backoff
- Clear separation of concerns (API ↔ workers)
- Consistent infrastructure pattern across all projects

### Negative / Trade-offs
- Redis + Celery workers are additional components to deploy and monitor per service

### Risks
- **Risk:** Task queue backs up under load
  - **Mitigation:** HPA on Celery workers, monitor queue depth via Prometheus

---

## Implementation Notes

- Redis connection via Azure Cache for Redis, credentials in Key Vault
- Azure Communication Services connection string stored in Azure Key Vault
- Use Celery `autoretry_for` with exponential backoff for transient failures
- Standard Celery worker deployment: separate Kubernetes Deployment with its own HPA

---

## References
- `governance/enterprise-standards.md` — Framework Policy (Celery + Redis)
- Project-level ADRs that inherit this decision: ADR-0008 (expense-portal)
- Related: ADR-0001 (language selection), ADR-0002 (data storage)
