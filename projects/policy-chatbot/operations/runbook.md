# Runbook: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-16
> **Produced by:** Monitor Agent
> **Service owner:** Platform Engineering
> **On-call rotation:** Azure Monitor Action Groups → PagerDuty rotation "Policy Chatbot"

---

## Service Overview

The Corporate Policy Assistant Chatbot is a conversational AI system that serves
~8,000 employees across 12 office locations. It answers policy questions grounded
in the corporate policy corpus using retrieval-augmented generation (RAG), provides
actionable checklists, and escalates to live service desk agents when it cannot
help. The system is accessible via Microsoft Teams and a web-based intranet widget.

Downtime directly impacts employee productivity (users revert to emailing HR,
adding ~15–30 min per query) and increases HR Service Desk ticket volume (~340
policy inquiries/week baseline).

---

## Architecture Quick Reference

```
Employee → Teams Bot / Web Widget
            ↓
      Azure API Management (TLS, rate limiting, CORS)
            ↓
      Azure Container Apps (FastAPI API server)
            ↓
    ┌───────┼───────────────────┐
    ↓       ↓                   ↓
PostgreSQL  Azure Cache    Azure AI Search
            for Redis
    ↓       ↓                   ↓
Azure       Azure OpenAI   Azure Blob
Key Vault   Service        Storage
```

| Component | Type | Dependencies |
|-----------|------|-------------|
| Chat & Admin API | FastAPI on ACA | PostgreSQL, Redis, Azure AI Search, Azure OpenAI, ServiceNow |
| PostgreSQL | Azure DB for PostgreSQL Flexible Server | — |
| Redis | Azure Cache for Redis | — |
| Azure AI Search | Azure AI Search (Standard) | — |
| Azure OpenAI | Azure OpenAI Service (GPT-4o) | — |
| Blob Storage | Azure Blob Storage | — |

---

## SLOs

| SLO | Target | Error Budget (30d) | Alert |
|-----|--------|-------------------|-------|
| API Availability | 99.5% non-5xx | 216 min/month | Burn rate > 2x → page; > 1x for 1h → ticket |
| API Latency | p95 < 5000ms | — | p95 > 5000ms for 3 windows → page |
| LLM Availability | 99% full RAG (not fallback) | — | > 5 fallbacks in 10 min → page |
| Resolution Rate | ≥ 70% without escalation | — | Escalation rate > 30% for 24h → ticket |

---

## Alert Response Procedures

### HighErrorRate

**Severity:** Critical (Sev 0)
**Impact:** Employees cannot get policy answers; queries fail with errors.

**Immediate triage (< 5 min):**
1. Check ACA replica status:
   ```bash
   az containerapp replica list \
     --name policy-chatbot-production-api \
     --resource-group rg-policy-chatbot-prod \
     -o table
   ```
2. Check Application Insights for error details:
   ```kql
   requests
   | where timestamp > ago(15m)
   | where resultCode startswith "5"
   | summarize count() by resultCode, name
   | order by count_ desc
   ```
3. Check recent deployments:
   ```bash
   az containerapp revision list \
     --name policy-chatbot-production-api \
     --resource-group rg-policy-chatbot-prod \
     -o table
   ```

**Common causes:**
- **Bad deployment** → Roll back to previous revision:
  ```bash
  az containerapp revision activate \
    --name policy-chatbot-production-api \
    --resource-group rg-policy-chatbot-prod \
    --revision <previous-revision-name>
  ```
- **PostgreSQL connection pool exhaustion** → Check active connections:
  ```kql
  dependencies
  | where timestamp > ago(15m)
  | where type == "SQL"
  | where success == false
  | summarize count() by resultCode
  ```
- **Azure OpenAI quota exceeded** → Check Azure OpenAI metrics in Azure Portal; request quota increase if needed
- **Azure AI Search outage** → Check Azure service health dashboard

**Escalation:** On-call → Platform Engineering lead → VP Employee Experience (if > 30 min)

---

### HighLatency

**Severity:** Warning (Sev 2)
**Impact:** Employees experience slow responses; may abandon and escalate to HR.

**Immediate triage:**
1. Check p95 latency breakdown by endpoint:
   ```kql
   requests
   | where timestamp > ago(30m)
   | where name !in ("/health", "/ready")
   | summarize p95 = percentile(duration, 95) by name
   | order by p95 desc
   ```
2. Check Azure OpenAI response latency:
   ```kql
   dependencies
   | where timestamp > ago(30m)
   | where type == "HTTP" and target contains "openai"
   | summarize p95 = percentile(duration, 95)
   ```
3. Check Azure AI Search query latency:
   ```kql
   dependencies
   | where timestamp > ago(30m)
   | where type == "HTTP" and target contains "search"
   | summarize p95 = percentile(duration, 95)
   ```

**Common causes:**
- **Azure OpenAI throttling** → Reduce concurrent requests; check token quota
- **Azure AI Search index performance** → Check index size; consider scaling replicas
- **Large conversation history** → Verify conversation context window is capped at 10 messages
- **Cold start after scaling** → Check ACA scaling events; pre-warm with min replicas ≥ 2

**Escalation:** On-call → Platform Engineering lead

---

### ServiceDown

**Severity:** Critical (Sev 0)
**Impact:** Complete service outage — no employee can use the chatbot.

**Immediate triage (< 2 min):**
1. Check ACA container status:
   ```bash
   az containerapp show \
     --name policy-chatbot-production-api \
     --resource-group rg-policy-chatbot-prod \
     --query "properties.runningStatus" -o tsv
   ```
2. Check ACA system logs:
   ```bash
   az containerapp logs show \
     --name policy-chatbot-production-api \
     --resource-group rg-policy-chatbot-prod \
     --type system
   ```
3. Check for failed provisioning:
   ```bash
   az containerapp revision list \
     --name policy-chatbot-production-api \
     --resource-group rg-policy-chatbot-prod \
     --query "[?properties.runningState!='Running']" -o table
   ```

**Common causes:**
- **Failed deployment** → Activate previous revision (see HighErrorRate rollback)
- **OOMKilled** → Increase memory limit in `main.prod.bicepparam`; redeploy
- **Image pull failure** → Check ACR connectivity; verify image tag exists
- **Key Vault secret rotation** → Verify secrets are current; restart revision

**Escalation:** On-call → Platform Engineering lead → VP Employee Experience immediately

---

### HighMemoryUsage

**Severity:** Warning (Sev 2)
**Impact:** Risk of OOMKilled → container restart → brief availability degradation.

**Immediate triage:**
1. Check memory usage per replica:
   ```kql
   performanceCounters
   | where timestamp > ago(1h)
   | where name == "% Process Memory"
   | summarize avg_memory = avg(value), max_memory = max(value) by cloud_RoleInstance
   ```
2. Check for memory leaks — trend over 24h:
   ```kql
   performanceCounters
   | where timestamp > ago(24h)
   | where name == "% Process Memory"
   | summarize avg_memory = avg(value) by bin(timestamp, 1h)
   | render timechart
   ```

**Common causes:**
- **Conversation history accumulation** → Verify Redis TTL is set correctly (90 days)
- **Large document processing** → Check if a re-indexing job is running; large PDFs may spike memory
- **Memory leak in application code** → Requires code investigation; file a bug

**Escalation:** On-call → Platform Engineering lead

---

### SLOBurnRateFast

**Severity:** Critical (Sev 0)
**Impact:** Error budget is being consumed at > 2x the sustainable rate. At this burn rate, the entire monthly budget will be exhausted in < 15 days.

**Triage:** Follow the same steps as **HighErrorRate** above. This alert fires earlier and is more sensitive — it detects trends before the error rate becomes visibly high.

**Action:** Identify and fix the root cause within 30 minutes, or roll back the most recent deployment.

---

### SLOBurnRateSlow

**Severity:** Warning (Sev 2)
**Impact:** Error budget is being consumed faster than sustainable. If uncorrected, the budget will exhaust before month-end.

**Triage:** Follow the same steps as **HighErrorRate** above, but with less urgency. Check for intermittent failures that don't trigger the fast burn alert.

**Action:** File a ticket; investigate within 24 hours. Consider pausing deployments until the trend reverses.

---

### LLMUnavailable

**Severity:** High (Sev 1)
**Impact:** Employees receive keyword search results instead of full AI answers. Answer quality degrades significantly. Escalation volume will likely increase.

**Immediate triage:**
1. Check Azure OpenAI service health:
   ```bash
   az cognitiveservices account show \
     --name policy-chatbot-openai \
     --resource-group rg-policy-chatbot-prod \
     -o table
   ```
2. Check Azure OpenAI endpoint connectivity from ACA:
   ```kql
   dependencies
   | where timestamp > ago(15m)
   | where type == "HTTP" and target contains "openai"
   | where success == false
   | summarize count() by resultCode
   ```
3. Check Azure service health: https://status.azure.com

**Common causes:**
- **Azure OpenAI regional outage** → Wait for Azure resolution; system auto-fallbacks to keyword search
- **Token quota exceeded** → Request quota increase via Azure Portal; reduce `max_tokens` temporarily
- **Network connectivity** → Check ACA → OpenAI VNET connectivity

**Action:** If Azure OpenAI is down regionally, communicate to stakeholders that the chatbot is in "basic search mode." No rollback needed — fallback mode is by design (NFR-006).

---

### HighEscalationRate

**Severity:** Warning (Sev 2)
**Impact:** More than 30% of conversations are escalating to human agents, exceeding the 70% self-service target. HR Service Desk will experience increased load.

**Triage:**
1. Check which topics are driving escalations:
   ```kql
   customEvents
   | where timestamp > ago(24h)
   | where name == "ConversationClosed"
   | where customDimensions.status == "escalated"
   | summarize count() by tostring(customDimensions.intent)
   | order by count_ desc
   ```
2. Check if specific policy domains are causing issues:
   ```kql
   customEvents
   | where timestamp > ago(24h)
   | where name == "ChatResponse"
   | where customDimensions.response_type == "no_match"
   | summarize count() by tostring(customDimensions.query)
   | order by count_ desc
   ```
3. Check the admin console flagged topics dashboard

**Common causes:**
- **Missing policy documents** → Admin needs to upload missing documents and re-index
- **Poor retrieval quality** → Chunking strategy may need tuning; review search relevance
- **New policy topic not yet indexed** → Upload the new document via admin console
- **Prompt quality degradation** → Review system prompt; check for Azure OpenAI model version changes

**Action:** File a ticket for the policy team to review unanswered queries and upload missing documents. This is not an infrastructure issue — it's a content coverage gap.

---

## Dashboards

| Dashboard | Location | Purpose |
|-----------|----------|---------|
| Service Overview | Azure Monitor Workbook | Error rate, latency, throughput, replica count |
| SLO Tracker | Azure Monitor Workbook | Error budget burn, SLO compliance |
| Business Metrics | Azure Monitor Workbook | Resolution rate, escalation rate, satisfaction, top intents |
| Infrastructure | Azure Portal → ACA | CPU, memory, scaling events, revision status |

---

## Contacts

| Role | Name / Team | Contact |
|------|-------------|---------|
| Service Owner | Platform Engineering | platform-engineering@acme.com |
| Product Owner | HR Service Desk Manager | hr-servicedesk@acme.com |
| Executive Sponsor | VP Employee Experience | via Teams |
| On-Call Primary | Platform Engineering rotation | PagerDuty → Azure Monitor Action Groups |
| Azure OpenAI Support | Microsoft Support | Azure Support ticket (Sev B) |
