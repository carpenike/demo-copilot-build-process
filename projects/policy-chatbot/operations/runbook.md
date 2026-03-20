# Runbook: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-20
> **Produced by:** Monitor Agent
> **Service owner:** Platform Engineering
> **On-call rotation:** Azure Monitor Action Groups — `policy-chatbot-critical`, `policy-chatbot-warning`

---

## Service Overview

The Policy Chatbot is a conversational AI service that answers employee questions
about corporate policy. It ingests ~140 policy documents from SharePoint, intranet
CMS, and blob storage, indexes them in Azure AI Search, and generates grounded
answers using Azure OpenAI (GPT-4o) with RAG. Approximately 8,000 employees
depend on this service via Microsoft Teams and the intranet web widget.

The HR Service Desk is the primary stakeholder — the chatbot is designed to
deflect ~340 policy inquiries per week. Service degradation directly increases
service desk ticket volume.

---

## Architecture Quick Reference

```
Employee (Teams / Intranet Widget)
        │
        ▼
Azure Container Apps (FastAPI)
  ├── Azure Cache for Redis (session/conversation cache)
  ├── Azure Database for PostgreSQL Flexible Server (conversations, feedback, documents metadata)
  ├── Azure AI Search (policy document index)
  ├── Azure Blob Storage (policy document files)
  ├── Azure OpenAI Service (GPT-4o — answer generation)
  └── Azure Key Vault (secrets)
        │
        ▼
Application Insights + Log Analytics (observability)
```

| Component | Type | Resource Name Pattern |
|-----------|------|-----------------------|
| API | FastAPI on Azure Container Apps | `{prefix}-api` |
| Database | PostgreSQL Flexible Server | `{prefix}-db` |
| Cache | Azure Cache for Redis | `{prefix}-redis` |
| Search | Azure AI Search | `{prefix}-search` |
| Storage | Azure Blob Storage | `{prefix}storage` |
| LLM | Azure OpenAI Service | `{prefix}-openai` |
| Secrets | Azure Key Vault | `{prefix}-kv` |
| Monitoring | Application Insights + Log Analytics | `{prefix}-insights`, `{prefix}-logs` |

---

## SLOs

| SLO | Target | Error Budget (30d) | Alert |
|-----|--------|-------------------|-------|
| API Availability | 99.5% non-5xx (NFR-004) | 3.6 hours | Burn rate > 2x → page; > 1x for 1h → ticket |
| Chat Latency | p95 < 5000ms (NFR-001) | — | p95 > 5000ms for 15 min → page |
| Non-Chat API Latency | p99 < 1000ms | — | p99 > 1000ms for 15 min → ticket |
| Document Indexing | Single doc < 5min (NFR-002) | — | Exceeds 5 min → ticket |
| LLM Dependency | 99.0% success | — | Failure rate > 10% for 5 min → page |

---

## Alert Response Procedures

### HighErrorRate

**Alert name:** `policy-chatbot-high-error-rate`
**Severity:** 0 (Critical)
**Condition:** 5xx error rate > 1% for 5 minutes
**SLO impact:** Availability SLO — burning error budget at > 2x rate
**Business impact:** Employees cannot get policy answers; HR Service Desk ticket volume increases

**Immediate triage (< 5 min):**
1. Open Application Insights → Failures blade → filter last 15 minutes
2. Identify the failing endpoint(s) and error codes:
   ```kql
   requests
   | where timestamp > ago(15m)
   | where resultCode startswith "5"
   | summarize count() by name, resultCode
   | order by count_ desc
   ```
3. Check if a deployment occurred in the last 30 minutes:
   ```kql
   customEvents
   | where timestamp > ago(30m)
   | where name == "DeploymentCompleted"
   ```
4. Check container health in Azure Portal → Container Apps → Revisions

**Common causes and remediation:**
| Cause | Diagnosis | Remediation |
|-------|-----------|-------------|
| Bad deployment | Errors started after recent revision activation | Roll back: `az containerapp revision deactivate` on the new revision, activate previous |
| Database connection pool exhaustion | Errors are `500` on data-access endpoints; dependency failures show PostgreSQL timeouts | Check PostgreSQL metrics (connections, CPU); restart app if pool is stuck; increase pool size if sustained |
| Azure OpenAI throttling (429→500) | Dependency failures on OpenAI calls | Verify quota in Azure Portal → OpenAI → Deployments; confirm fallback (NFR-006) is working |
| Redis connection failure | Session/cache errors in logs | Check Redis health in Azure Portal; test connectivity from container shell |

**Escalation path:** On-call engineer → Team lead → Platform Engineering manager

---

### HighLatencyChat

**Alert name:** `policy-chatbot-high-latency-chat`
**Severity:** 1 (High)
**Condition:** Chat endpoint p95 latency > 5000ms for 15 minutes
**SLO impact:** Chat Latency SLO violation
**Business impact:** Employees experience slow responses; may abandon chatbot and call HR directly

**Immediate triage (< 5 min):**
1. Check chat endpoint latency breakdown:
   ```kql
   requests
   | where timestamp > ago(30m)
   | where name startswith "/v1/chat"
   | summarize
       p50 = percentile(duration, 50),
       p95 = percentile(duration, 95),
       p99 = percentile(duration, 99)
       by bin(timestamp, 5m)
   | order by timestamp desc
   ```
2. Check dependency latency (identify the slow component):
   ```kql
   dependencies
   | where timestamp > ago(30m)
   | summarize avg_duration = avg(duration), p95_duration = percentile(duration, 95) by target, type
   | order by p95_duration desc
   ```
3. Check if Azure OpenAI response time has increased:
   ```kql
   dependencies
   | where timestamp > ago(30m)
   | where target contains "openai"
   | summarize p95 = percentile(duration, 95) by bin(timestamp, 5m)
   ```

**Common causes and remediation:**
| Cause | Diagnosis | Remediation |
|-------|-----------|-------------|
| Azure OpenAI latency spike | OpenAI dependency p95 is elevated | Check Azure OpenAI service health; consider reducing `max_tokens`; verify model deployment region |
| Azure AI Search slow queries | Search dependency latency elevated | Check search index size and query complexity; review search service tier scaling |
| Database slow queries | PostgreSQL dependency latency elevated | Run `pg_stat_activity` to find long-running queries; check for missing indexes |
| High concurrency | Request count significantly elevated | Check scaling rules; manually scale up replicas: `az containerapp update --min-replicas` |

**Escalation path:** On-call engineer → Team lead → Platform Engineering manager

---

### HighLatencyApi

**Alert name:** `policy-chatbot-high-latency-api`
**Severity:** 2 (Warning)
**Condition:** Non-chat API p99 latency > 1000ms for 15 minutes
**Business impact:** Admin console and conversation history loading slowly; degraded user experience

**Immediate triage:**
1. Identify which non-chat endpoint is slow:
   ```kql
   requests
   | where timestamp > ago(30m)
   | where name !in ("/health", "/ready")
   | where name !startswith "/v1/chat"
   | summarize p99 = percentile(duration, 99), count() by name
   | where p99 > 1000
   | order by p99 desc
   ```
2. Check database query performance for the affected endpoints
3. Check Redis cache hit rate — low hit rate increases DB load

**Common causes and remediation:**
| Cause | Diagnosis | Remediation |
|-------|-----------|-------------|
| Missing database index | Specific query pattern is slow | Add index; coordinate with development team |
| Redis cache miss storm | Cache was recently flushed or expired | Investigate cache TTL settings; warm cache if needed |
| Large result sets | Pagination not working correctly | Check cursor-based pagination implementation |

**Escalation path:** On-call engineer → Team lead

---

### ServiceDown

**Alert name:** `policy-chatbot-service-down`
**Severity:** 0 (Critical)
**Condition:** No healthy container replicas for 5 minutes
**Business impact:** Complete chatbot outage — all employee queries fail; HR Service Desk load increases immediately

**Immediate triage (< 2 min):**
1. Check Container App status in Azure Portal:
   - Container Apps → `{prefix}-api` → Revisions & replicas
2. Check revision provisioning status:
   ```bash
   az containerapp revision list --name {prefix}-api --resource-group {rg} -o table
   ```
3. Check container logs for crash reasons:
   ```kql
   ContainerAppConsoleLogs_CL
   | where ContainerAppName_s == "{prefix}-api"
   | where timestamp > ago(15m)
   | order by timestamp desc
   | take 50
   ```

**Common causes and remediation:**
| Cause | Diagnosis | Remediation |
|-------|-----------|-------------|
| Failed deployment | New revision in "Failed" state | Deactivate failed revision; activate last known good: `az containerapp revision activate` |
| OOM killed | Logs show `OOMKilled` | Increase memory limit in container app config; investigate memory leak |
| Readiness probe failure | `/ready` returns 503 — a dependency is down | Identify which dependency check is failing in `/ready` response; fix upstream |
| Secret rotation | Key Vault secret expired or rotated without app restart | Restart revision to pick up new secrets: `az containerapp revision restart` |
| ACR pull failure | Image pull errors in events | Verify ACR credentials and image tag exist |

**Escalation path:** On-call engineer → Team lead → Platform Engineering manager (immediately)

---

### HighMemoryUsage

**Alert name:** `policy-chatbot-high-memory-usage`
**Severity:** 2 (Warning)
**Condition:** Container memory usage > 80% of limit for 10 minutes
**Business impact:** Risk of OOM kill leading to service disruption

**Immediate triage:**
1. Check current memory usage:
   ```kql
   performanceCounters
   | where timestamp > ago(1h)
   | where category == "Process"
   | where name == "Private Bytes"
   | summarize avg_bytes = avg(value) by bin(timestamp, 5m)
   | order by timestamp desc
   ```
2. Check for memory growth trend (leak detection):
   ```kql
   performanceCounters
   | where timestamp > ago(24h)
   | where category == "Process"
   | where name == "Private Bytes"
   | summarize avg_bytes = avg(value) by bin(timestamp, 1h)
   | order by timestamp asc
   ```

**Common causes and remediation:**
| Cause | Diagnosis | Remediation |
|-------|-----------|-------------|
| Memory leak | Steady upward trend over hours/days | Identify leaking component; restart as short-term fix; file bug |
| Large document processing | Spike correlates with document upload/indexing | Monitor indexing jobs; consider processing large docs asynchronously with lower concurrency |
| Connection pool growth | Many idle connections held in memory | Review connection pool max size settings |

**Escalation path:** On-call engineer → Team lead

---

### SLOBurnRateFast

**Alert name:** `policy-chatbot-slo-burn-fast`
**Severity:** 0 (Critical)
**Condition:** Error rate > 1% for 5 minutes (availability budget burning at > 2x sustainable rate)
**SLO impact:** Will exhaust 30-day error budget in < 15 days at this rate

**Triage:** Follow the same procedure as [HighErrorRate](#higherrorrate). This alert uses
the same underlying signal but is framed in SLO burn rate terms. The key difference
is urgency — at 2x burn rate, the monthly error budget will be consumed in half the
window period.

**Action:** Treat as a high-urgency incident. If not resolved within 15 minutes, escalate.

---

### SLOBurnRateSlow

**Alert name:** `policy-chatbot-slo-burn-slow`
**Severity:** 2 (Warning)
**Condition:** Error rate > 0.5% sustained for 1 hour (budget burning at > 1x sustainable rate)
**SLO impact:** If sustained, will exhaust error budget before end of 30-day window

**Triage:** Follow the same procedure as [HighErrorRate](#higherrorrate). The slower
burn rate means this may be a chronic issue rather than an acute incident.

**Action:**
1. Review recent changes (deployments, config updates, dependency changes)
2. Check if error rate is trending up or stable
3. Create a ticket for investigation if no obvious cause
4. Consider error budget policy actions (see SLO Definitions)

---

### LLMDependencyFailure

**Alert name:** `policy-chatbot-llm-dependency-failure`
**Severity:** 1 (High)
**Condition:** Azure OpenAI failure rate > 10% for 5 minutes
**Business impact:** Chatbot enters keyword-search fallback mode (NFR-006); answer quality degrades significantly

**Immediate triage (< 5 min):**
1. Check Azure OpenAI dependency health:
   ```kql
   dependencies
   | where timestamp > ago(15m)
   | where target contains "openai"
   | summarize
       total = count(),
       failures = countif(success == false),
       p95_latency = percentile(duration, 95)
       by bin(timestamp, 5m)
   ```
2. Check Azure OpenAI error codes:
   ```kql
   dependencies
   | where timestamp > ago(15m)
   | where target contains "openai"
   | where success == false
   | summarize count() by resultCode
   ```
3. Check Azure OpenAI service health: Azure Portal → Azure OpenAI → Deployments
4. Check [Azure Status page](https://status.azure.com) for regional outages

**Common causes and remediation:**
| Cause | Diagnosis | Remediation |
|-------|-----------|-------------|
| Rate limiting (429) | `resultCode` is 429; high request volume | Verify TPM quota; consider request queuing or retry with backoff |
| Azure OpenAI outage | All calls failing with 5xx | Confirm via Azure Status; wait for recovery; fallback mode should be active (NFR-006) |
| Token limit exceeded | 400 errors with token-related messages | Review prompt construction; reduce context window size |
| Network/DNS issue | Connection timeouts | Check Container App outbound connectivity; verify DNS resolution |

**Verification — confirm fallback is active:**
```kql
requests
| where timestamp > ago(15m)
| where name startswith "/v1/chat"
| where customDimensions.response_type == "fallback_search"
| summarize count()
```

**Escalation path:** On-call engineer → Team lead → Platform Engineering manager (if Azure service issue, file support ticket)

---

### DatabaseConnectionFailure

**Alert name:** `policy-chatbot-database-failure`
**Severity:** 0 (Critical)
**Condition:** PostgreSQL dependency failure rate > 10% for 5 minutes
**Business impact:** Conversation history, feedback, and document management non-functional; chat may still work with cached data

**Immediate triage (< 5 min):**
1. Check database dependency status:
   ```kql
   dependencies
   | where timestamp > ago(15m)
   | where type == "SQL" or target contains "postgres"
   | summarize
       total = count(),
       failures = countif(success == false),
       avg_latency = avg(duration)
       by bin(timestamp, 5m)
   ```
2. Check PostgreSQL server health:
   ```bash
   az postgres flexible-server show --name {prefix}-db --resource-group {rg} -o table
   ```
3. Check connection count:
   ```bash
   az postgres flexible-server parameter show --name max_connections \
     --server-name {prefix}-db --resource-group {rg}
   ```

**Common causes and remediation:**
| Cause | Diagnosis | Remediation |
|-------|-----------|-------------|
| Connection pool exhaustion | Many connections in `idle in transaction` state | Restart application; review connection pool settings |
| PostgreSQL server restart | Server shows recent restart event | Wait for recovery; connections will auto-reconnect |
| Firewall rule change | Connection refused errors | Verify firewall rules allow Container App outbound IP |
| Storage limit reached | Write errors in PostgreSQL logs | Increase storage; clean up old conversation logs (NFR-008: 90-day retention) |

**Escalation path:** On-call engineer → Team lead → DBA / Platform Engineering manager

---

### SearchIndexStale

**Alert name:** `policy-chatbot-search-index-stale`
**Severity:** 2 (Warning)
**Condition:** Document indexing job exceeded 5-minute SLO (NFR-002)
**Business impact:** Newly uploaded policy documents not searchable within expected timeframe; employees may get outdated answers

**Immediate triage:**
1. Check recent indexing job durations:
   ```kql
   customMetrics
   | where timestamp > ago(1h)
   | where name == "document_indexing_duration_seconds"
   | project timestamp, value, customDimensions
   | order by timestamp desc
   ```
2. Check Azure AI Search service metrics:
   - Azure Portal → AI Search → Metrics → Document count, Query latency
3. Check if a full corpus re-index is running (NFR-003: expected to take up to 2 hours)

**Common causes and remediation:**
| Cause | Diagnosis | Remediation |
|-------|-----------|-------------|
| Large document (>200 pages) | `customDimensions.page_count` is high | Expected for very large docs; adjust alert threshold or split document |
| Full corpus re-index in progress | Admin triggered full re-index | Expected behavior — full re-index can take up to 2 hours (NFR-003) |
| Azure AI Search throttling | Search service metrics show throttling | Scale up search service tier or add replicas |
| Blob Storage access failure | Indexer errors referencing blob access | Check blob storage firewall rules and managed identity permissions |

**Escalation path:** On-call engineer → Team lead

---

### HighConcurrency

**Alert name:** `policy-chatbot-high-concurrency`
**Severity:** 2 (Warning)
**Condition:** Active concurrent requests > 150 (75% of 200 normal capacity, NFR-013)
**Business impact:** Approaching capacity limit; risk of degraded response times or request rejection

**Immediate triage:**
1. Check current request rate and concurrency:
   ```kql
   requests
   | where timestamp > ago(30m)
   | summarize request_count = count() by bin(timestamp, 1m)
   | order by timestamp desc
   ```
2. Check if auto-scaling has triggered:
   ```bash
   az containerapp revision list --name {prefix}-api --resource-group {rg} \
     --query "[].{name:name, replicas:properties.replicas}" -o table
   ```
3. Verify scaling rules are configured correctly

**Common causes and remediation:**
| Cause | Diagnosis | Remediation |
|-------|-----------|-------------|
| Organic traffic spike | Gradual increase correlating with business event | Scale up replicas; monitor if sustained |
| Bot/automated traffic | Sudden spike from single IP or user agent | Identify source; apply rate limiting |
| Slow downstream responses | Requests piling up due to slow OpenAI or Database | Fix downstream issue first (see relevant alert procedures) |

**Escalation path:** On-call engineer → Team lead

---

## Dependency Health Checks

The `/ready` endpoint checks all dependencies. Use it for quick health verification:

```bash
curl -s https://{service-url}/ready | jq .
```

Expected healthy response:
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "search": "ok",
    "openai": "ok"
  }
}
```

If any check fails, the service reports `503` and ACA will stop routing traffic to that instance.

---

## Rollback Procedure

1. List revisions:
   ```bash
   az containerapp revision list --name {prefix}-api --resource-group {rg} -o table
   ```
2. Identify the last known good revision
3. Activate the good revision:
   ```bash
   az containerapp revision activate --name {prefix}-api --resource-group {rg} \
     --revision {last-good-revision-name}
   ```
4. Deactivate the bad revision:
   ```bash
   az containerapp revision deactivate --name {prefix}-api --resource-group {rg} \
     --revision {bad-revision-name}
   ```
5. Set traffic to 100% on the good revision:
   ```bash
   az containerapp ingress traffic set --name {prefix}-api --resource-group {rg} \
     --revision-weight {last-good-revision-name}=100
   ```
6. Verify service health: `curl -s https://{service-url}/ready | jq .`

---

## Contacts

| Role | Contact | Method |
|------|---------|--------|
| On-call engineer | PagerDuty rotation | Azure Monitor → Action Group → PagerDuty |
| Platform Engineering lead | Platform Engineering team | Teams channel: #platform-engineering |
| HR Service Desk (stakeholder) | HR Service Desk Manager | Email: hr-servicedesk-mgr@acme.com |
| Azure OpenAI support | Microsoft Support | Azure Support ticket (Sev B for degradation, Sev A for outage) |
| Database admin | Platform Engineering DBA | Teams channel: #database-ops |
