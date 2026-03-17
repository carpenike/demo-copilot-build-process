# Runbook: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-17
> **Produced by:** Monitor Agent
> **Service owner:** Platform Engineering
> **On-call rotation:** Azure Monitor Action Groups

---

## Service Overview

The Corporate Policy Assistant Chatbot is a RAG-powered conversational AI
service that answers employee questions about corporate policies. It serves
~8,000 employees via Microsoft Teams and an intranet web widget, handling up to
200 concurrent conversations. The service ingests 140+ policy documents, indexes
them in Azure AI Search, and generates cited answers using Azure OpenAI GPT-4o.

**Business impact of outage:** HR Service Desk ticket volume increases by ~340
inquiries/week. Employees cannot self-serve policy questions.

---

## Architecture Quick Reference

```
Employee → Teams / Web Chat → Azure Bot Service → ACA (FastAPI API)
                                                      ↓
                                              Azure AI Search (retrieval)
                                              Azure OpenAI (generation)
                                              PostgreSQL (state)
                                              Redis (cache + Celery broker)
                                              Blob Storage (documents)
                                                      ↓
Admin → Admin API (ACA) → Document CRUD, Analytics
                                                      ↓
Worker → ACA Worker → Celery (document indexing)
```

| Component | Type | Dependencies |
|-----------|------|-------------|
| API | Azure Container Apps (FastAPI) | PostgreSQL, Redis, Azure OpenAI, AI Search, Blob Storage |
| Worker | Azure Container Apps (Celery) | PostgreSQL, Redis, Azure OpenAI, AI Search, Blob Storage |
| Database | Azure Database for PostgreSQL | — |
| Cache | Azure Cache for Redis | — |
| Search | Azure AI Search | — |
| LLM | Azure OpenAI Service | — |

---

## SLOs

| SLO | Target | Error Budget (30d) | Alert |
|-----|--------|-------------------|-------|
| API Availability | 99.5% non-5xx | 3.6 hours | Burn rate > 14.4x → page; > 1x for 1h → ticket |
| API Latency | p95 < 5000ms | — | p95 > 5s for 3 windows → page |
| LLM Dependency | 99.0% success | — | Failure rate > 5% for 10m → page |
| Resolution Rate | ≥ 70% self-service | — | Rate < 70% for 24h → ticket |

---

## Alert Response Procedures

### HighErrorRate

**Severity:** Critical (Sev 0)
**SLO:** 99.5% availability (NFR-004)
**Threshold:** 5xx error rate > 0.5% for 5 minutes
**Impact:** Employees receive errors when asking policy questions

**Immediate triage (< 5 min):**
1. Check ACA revision status:
   ```bash
   az containerapp show --name policy-chatbot-{env}-api \
     --resource-group rg-policy-chatbot-{env} \
     --query "properties.latestRevisionName" -o tsv
   ```
2. Check container logs for crash loops:
   ```bash
   az containerapp logs show --name policy-chatbot-{env}-api \
     --resource-group rg-policy-chatbot-{env} --tail 50
   ```
3. Check Application Insights for error patterns:
   ```kql
   requests
   | where timestamp > ago(15m)
   | where resultCode startswith "5"
   | summarize count() by name, resultCode
   | order by count_ desc
   ```

**Common causes and remediation:**
- **Database connection failures** → Check PostgreSQL status in Azure Portal; verify connection string in Key Vault is correct
- **Redis connection timeout** → Check Redis metrics in Azure Portal; verify Redis is not at max memory
- **Bad deployment** → Roll back to previous revision:
  ```bash
  az containerapp revision list --name policy-chatbot-{env}-api \
    --resource-group rg-policy-chatbot-{env} -o table
  az containerapp ingress traffic set --name policy-chatbot-{env}-api \
    --resource-group rg-policy-chatbot-{env} \
    --revision-weight <previous-revision>=100
  ```
- **Upstream dependency outage** → Check Azure Status page; verify AI Search and OpenAI endpoints

**Escalation:** On-call → Platform Engineering Lead → VP Engineering

---

### HighLatency

**Severity:** Warning (Sev 2)
**SLO:** p95 < 5000ms (NFR-001)
**Threshold:** p95 > 5000ms for 15 minutes
**Impact:** Employees experience slow responses; may perceive service as broken

**Immediate triage (< 10 min):**
1. Check if Azure OpenAI is throttling (429 responses):
   ```kql
   dependencies
   | where timestamp > ago(15m)
   | where target contains "openai"
   | summarize count() by resultCode
   ```
2. Check if AI Search is slow:
   ```kql
   dependencies
   | where timestamp > ago(15m)
   | where target contains "search"
   | summarize avg(duration), percentile(duration, 95)
   ```
3. Check container CPU/memory utilization

**Common causes and remediation:**
- **Azure OpenAI throttling (429s)** → Increase TPM quota in Azure Portal; check if token usage has spiked
- **AI Search query latency** → Check index size and query complexity; consider replica increase
- **Database slow queries** → Check PostgreSQL slow query log; verify indexes exist
- **Insufficient ACA replicas** → Scale up manually:
  ```bash
  az containerapp update --name policy-chatbot-{env}-api \
    --resource-group rg-policy-chatbot-{env} --min-replicas 4
  ```

**Escalation:** On-call → Platform Engineering Lead

---

### ServiceDown

**Severity:** Critical (Sev 0)
**Threshold:** Zero successful requests for 5 minutes
**Impact:** Service is completely unavailable; all employees affected

**Immediate triage (< 5 min):**
1. Check ACA provisioning state:
   ```bash
   az containerapp show --name policy-chatbot-{env}-api \
     --resource-group rg-policy-chatbot-{env} \
     --query "properties.provisioningState" -o tsv
   ```
2. Check if ACA environment is healthy:
   ```bash
   az containerapp env show --name policy-chatbot-{env}-env \
     --resource-group rg-policy-chatbot-{env} \
     --query "properties.provisioningState" -o tsv
   ```
3. Check container startup logs:
   ```bash
   az containerapp logs show --name policy-chatbot-{env}-api \
     --resource-group rg-policy-chatbot-{env} --type system --tail 20
   ```

**Common causes and remediation:**
- **Container crash loop** → Check system logs for OOM kill or startup errors; roll back revision
- **Key Vault access failure** → Verify managed identity has `Key Vault Secrets User` role; check Key Vault firewall
- **ACR pull failure** → Verify managed identity has `AcrPull` role; check if image tag exists
- **ACA environment issue** → Check Azure Status page for ACA region outage

**Escalation:** On-call → Platform Engineering Lead → Azure Support (if platform issue)

---

### HighMemoryUsage

**Severity:** Warning (Sev 2)
**Threshold:** Memory > 80% of container limit for 10 minutes
**Impact:** Service may become unstable; OOM kill risk

**Immediate triage (< 10 min):**
1. Check current memory usage:
   ```kql
   performanceCounters
   | where timestamp > ago(30m)
   | where category == "Process" and counter == "Working Set"
   | summarize avg(value) by bin(timestamp, 1m)
   | render timechart
   ```
2. Check if conversation count has spiked:
   ```kql
   requests
   | where timestamp > ago(1h)
   | summarize count() by bin(timestamp, 5m)
   | render timechart
   ```

**Common causes and remediation:**
- **Memory leak** → Restart the container app (new revision with same image); investigate if recent deployment introduced leak
- **Excessive concurrent conversations** → Check if scaling rules are firing; increase max replicas
- **Large document processing** → Check if a bulk re-index is in progress consuming worker memory

**Escalation:** On-call → Platform Engineering Lead

---

### SLOBurnRateFast

**Severity:** Critical (Sev 0)
**SLO:** 99.5% availability (NFR-004)
**Threshold:** Error budget burning at > 14.4x rate for 5 minutes (will exhaust entire monthly budget in ~1 hour)
**Impact:** Rapid error budget consumption — service reliability at risk

**Immediate triage (< 5 min):**
1. Follow the **HighErrorRate** runbook — this alert indicates the same root cause but at a more severe rate
2. Check if a bad deployment just went out:
   ```bash
   az containerapp revision list --name policy-chatbot-{env}-api \
     --resource-group rg-policy-chatbot-{env} --query "[0].{name:name, created:properties.createdTime}" -o table
   ```
3. If recent deployment → immediate rollback

**Escalation:** On-call → Platform Engineering Lead immediately

---

### SLOBurnRateSlow

**Severity:** Warning (Sev 2)
**SLO:** 99.5% availability (NFR-004)
**Threshold:** Error budget burning at > 1x sustained rate for 1 hour
**Impact:** Steady error rate that will exhaust the monthly budget if not addressed

**Triage (< 30 min):**
1. Check error rate trend over the last 4 hours — is it increasing, stable, or decreasing?
2. Identify the most common error types:
   ```kql
   requests
   | where timestamp > ago(4h)
   | where resultCode startswith "5"
   | summarize count() by name, resultCode, tostring(customDimensions)
   | order by count_ desc
   | take 10
   ```
3. Check if a specific endpoint is failing more than others

**Common causes and remediation:**
- **Intermittent dependency failure** → Check dependency health in Application Insights Failures blade
- **Partial deployment issue** → Check if old and new revisions are both receiving traffic
- **Database connection pool exhaustion** → Check PostgreSQL active connections; increase pool size if needed

**Escalation:** Create a ticket for the engineering team

---

### LLMDependencyDown

**Severity:** High (Sev 1)
**Threshold:** Azure OpenAI failure rate > 5% for 10 minutes
**Impact:** RAG pipeline degrades to keyword fallback (NFR-006); answer quality reduced

**Immediate triage (< 10 min):**
1. Check Azure OpenAI service health:
   ```bash
   az cognitiveservices account show --name policy-chatbot-{env}-openai \
     --resource-group rg-policy-chatbot-{env} \
     --query "properties.provisioningState" -o tsv
   ```
2. Check for throttling (429 Too Many Requests):
   ```kql
   dependencies
   | where timestamp > ago(15m)
   | where target contains "openai"
   | where resultCode == "429"
   | summarize count() by bin(timestamp, 1m)
   ```
3. Check Azure Status page for OpenAI service outage

**Common causes and remediation:**
- **Rate limiting (429)** → Increase TPM quota in Azure Portal → OpenAI resource → Quotas
- **Azure OpenAI service outage** → Wait for Azure to resolve; keyword fallback is active (NFR-006)
- **Managed identity token expiry** → Restart the container app to refresh tokens
- **Model deployment deleted/changed** → Verify model deployments exist:
  ```bash
  az cognitiveservices account deployment list \
    --name policy-chatbot-{env}-openai \
    --resource-group rg-policy-chatbot-{env} -o table
  ```

**Escalation:** On-call → Platform Engineering Lead; file Azure Support ticket if outage persists > 30 min

---

### HighEscalationRate

**Severity:** Warning (Sev 2)
**Threshold:** Auto-escalation rate > 25% over 1 hour
**Impact:** Chatbot is not resolving queries effectively; HR Service Desk may see increased ticket volume

**Triage (< 1 hour):**
1. Check which topics are being escalated:
   ```kql
   customEvents
   | where timestamp > ago(4h)
   | where name == "analytics_event"
   | where customDimensions.event_type == "escalation"
   | summarize count() by tostring(customDimensions.intent_domain)
   | order by count_ desc
   ```
2. Check if a specific policy domain has poor coverage (missing documents)
3. Check admin console for flagged topics with negative feedback

**Common causes and remediation:**
- **Missing policy documents** → Upload missing documents via admin console
- **Poor retrieval quality** → Check AI Search index health; consider re-indexing
- **Prompt drift** → Review recent changes to system prompts; revert if needed
- **New policy topic not indexed** → Upload and index the new policy document

**Escalation:** Create a ticket for the content team (HR Policy Team)

---

## Dependency Health Checks

| Dependency | Health Check | Expected |
|------------|-------------|----------|
| PostgreSQL | `SELECT 1` via `/ready` endpoint | Connected |
| Redis | `PING` via `/ready` endpoint | PONG |
| Azure OpenAI | Model list API call | 200 OK |
| Azure AI Search | Index list API call | 200 OK |

---

## Maintenance Procedures

### Planned Maintenance Window

1. Announce maintenance ≥ 48 hours in advance
2. Scale down to minimum replicas
3. Perform maintenance (database migration, index rebuild, etc.)
4. Verify `/health` and `/ready` endpoints
5. Scale back to normal replica count
6. Monitor error rate for 15 minutes post-maintenance

### Database Migration

```bash
az containerapp exec \
  --name policy-chatbot-{env}-api \
  --resource-group rg-policy-chatbot-{env} \
  --command "alembic upgrade head"
```

### Full Corpus Re-Index

Trigger via admin API:
```bash
curl -X POST https://{api-fqdn}/api/admin/reindex-all \
  -H "Authorization: Bearer {admin-token}"
```

Expected duration: up to 2 hours for ~140 documents (NFR-003).
