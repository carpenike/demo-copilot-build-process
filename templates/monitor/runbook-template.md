# Runbook: [Service Name]

> **Version:** 1.0
> **Date:** YYYY-MM-DD
> **Produced by:** Monitor Agent
> **Service owner:** [Team name]
> **On-call rotation:** [Azure Monitor Action Groups schedule link]

---

## Service Overview

[One paragraph: what this service does, who depends on it, and why it matters.]

---

## Architecture Quick Reference

```
[Text diagram or mermaid showing components and dependencies]
```

| Component | Type | Dependency |
|-----------|------|------------|
| [service] | FastAPI / Go HTTP | PostgreSQL, Redis, Workday API |

---

## SLOs

| SLO | Target | Error Budget (30d) | Alert |
|-----|--------|-------------------|-------|
| Availability | 99.9% non-5xx | 43.2 min | Burn rate > 2x → page |
| Latency | p99 < [X]ms | — | p99 > threshold for 3 windows → page |

---

## Alert Response Procedures

### HighErrorRate

**Severity:** Critical
**Impact:** [Business impact]

**Immediate triage (< 5 min):**
1. Check pod status: `kubectl get pods -n <namespace> -l app=<service>`
2. Check logs: `kubectl logs -n <namespace> -l app=<service> --since=10m`
3. Check error rate dashboard: [link]

**Common causes:**
- Upstream dependency outage → check [dependency] status
- DB connection pool exhaustion → check slow query log
- Bad deployment → `kubectl rollout undo deployment/<service>`

**Escalation:** On-call → Team lead → Service owner

---

### HighLatency

**Severity:** Warning → Critical
**Impact:** [Business impact]

**Immediate triage:**
1. Check p99 dashboard: [link]
2. Check for increased traffic: [link]
3. Check DB query performance

**Common causes:**
- Missing index on new query path
- Increased payload size
- Downstream dependency slowdown

---

### ServiceDown

**Severity:** Critical
**Impact:** Complete service outage

**Immediate triage:**
1. `kubectl get pods -n <namespace> -l app=<service>` — check for CrashLoopBackOff
2. `kubectl describe pod <pod-name>` — check events
3. Check recent deployments: `kubectl rollout history deployment/<service>`

**Common causes:**
- Failed deployment → rollback
- OOMKilled → increase memory limits
- Secret rotation failure → check External Secrets Operator

---

### PodRestartLoop

**Severity:** Warning
**Impact:** Degraded availability

**Triage:**
1. `kubectl logs <pod-name> --previous` — check crash reason
2. Check resource limits vs actual usage
3. Verify health check endpoints respond

---

## Dashboards

| Dashboard | URL | Purpose |
|-----------|-----|---------|
| Service Overview | [link] | Error rate, latency, throughput |
| Infrastructure | [link] | CPU, memory, pod count |
| Business Metrics | [link] | Domain-specific KPIs |

---

## Contacts

| Role | Name | Contact |
|------|------|---------|
| Service Owner | [name] | [email/teams] |
| On-Call Primary | [rotation] | [Azure Monitor Action Groups] |
| Escalation | [name] | [email/teams] |
