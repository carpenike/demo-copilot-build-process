# Dashboard Spec: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-16
> **Produced by:** Monitor Agent
> **Dashboard Platform:** Azure Monitor Workbooks (enterprise standard)
> **Data Sources:** Application Insights (KQL), Azure Container Apps metrics

---

## Dashboard 1: Service Overview

**Purpose:** Real-time operational health for on-call engineers.
**Audience:** Platform Engineering, on-call rotation
**Refresh interval:** 5 minutes

### Panels

#### 1.1 Error Rate (time chart)
```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| summarize
    total = count(),
    errors = countif(resultCode startswith "5")
    by bin(timestamp, 5m)
| extend error_rate = todouble(errors) / todouble(total) * 100
| project timestamp, error_rate
| render timechart
```
**Visualization:** Line chart with threshold line at 0.5% (SLO)

#### 1.2 p95 Latency (time chart)
```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| summarize p95_ms = percentile(duration, 95) by bin(timestamp, 5m)
| render timechart
```
**Visualization:** Line chart with threshold line at 5000ms (SLO from NFR-001)

#### 1.3 Throughput (time chart)
```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| summarize request_count = count() by bin(timestamp, 5m)
| render timechart
```
**Visualization:** Bar chart

#### 1.4 Active Replicas (time chart)
**Source:** Azure Container Apps metric `Replicas`
**Visualization:** Line chart showing current replica count over time

#### 1.5 Error Breakdown (pie chart)
```kql
requests
| where timestamp > ago(1h)
| where resultCode startswith "4" or resultCode startswith "5"
| summarize count() by resultCode
| render piechart
```

#### 1.6 Dependency Health (table)
```kql
dependencies
| where timestamp > ago(15m)
| summarize
    total = count(),
    failures = countif(success == false),
    p95_ms = percentile(duration, 95)
    by type, target
| extend success_rate = round((1.0 - todouble(failures) / todouble(total)) * 100, 2)
| project target, type, total, success_rate, p95_ms
| order by success_rate asc
```
**Visualization:** Table with conditional formatting (red if success_rate < 99%)

---

## Dashboard 2: SLO Tracker

**Purpose:** Track SLO compliance and error budget consumption.
**Audience:** Platform Engineering lead, VP Employee Experience
**Refresh interval:** 1 hour

### Panels

#### 2.1 Availability SLO — 30-Day Rolling (gauge)
```kql
requests
| where timestamp > ago(30d)
| where name !in ("/health", "/ready")
| summarize total = count(), errors = countif(resultCode startswith "5")
| extend availability = round((1.0 - todouble(errors) / todouble(total)) * 100, 3)
| project availability
```
**Visualization:** Gauge with target zone at 99.5% (green ≥ 99.5%, yellow 99.0–99.5%, red < 99.0%)

#### 2.2 Error Budget Remaining (stat)
```kql
requests
| where timestamp > ago(30d)
| where name !in ("/health", "/ready")
| summarize total = count(), errors = countif(resultCode startswith "5")
| extend error_rate = todouble(errors) / todouble(total)
| extend budget_target = 0.005  // 0.5% error budget for 99.5% SLO
| extend budget_consumed_pct = round((error_rate / budget_target) * 100, 1)
| extend budget_remaining_pct = max_of(0, 100 - budget_consumed_pct)
| project budget_remaining_pct
```
**Visualization:** Single stat with color thresholds (green > 50%, yellow 25–50%, red < 25%)

#### 2.3 Error Budget Burn Rate (time chart)
```kql
requests
| where timestamp > ago(7d)
| where name !in ("/health", "/ready")
| summarize
    total = count(),
    errors = countif(resultCode startswith "5")
    by bin(timestamp, 1h)
| extend error_rate = todouble(errors) / todouble(total)
| extend burn_rate = error_rate / 0.005
| project timestamp, burn_rate
| render timechart
```
**Visualization:** Line chart with threshold lines at 1x (sustainable) and 2x (fast burn)

#### 2.4 Latency SLO Compliance (gauge)
```kql
requests
| where timestamp > ago(30d)
| where name !in ("/health", "/ready")
| summarize p95_ms = percentile(duration, 95) by bin(timestamp, 5m)
| summarize
    total_windows = count(),
    compliant_windows = countif(p95_ms < 5000)
| extend compliance_pct = round(todouble(compliant_windows) / todouble(total_windows) * 100, 1)
| project compliance_pct
```
**Visualization:** Gauge with target at 95%

---

## Dashboard 3: Business Metrics

**Purpose:** Track business outcomes and chatbot effectiveness.
**Audience:** HR Service Desk Manager, VP Employee Experience, Product Owner
**Refresh interval:** 1 hour

### Panels

#### 3.1 Resolution Rate — 30-Day (stat)
```kql
customEvents
| where timestamp > ago(30d)
| where name == "ConversationClosed"
| summarize
    total = count(),
    resolved = countif(customDimensions.status != "escalated")
| extend resolution_rate = round(todouble(resolved) / todouble(total) * 100, 1)
| project resolution_rate
```
**Visualization:** Single stat (green ≥ 70%, red < 70%)

#### 3.2 Escalation Rate — 30-Day (stat)
```kql
customEvents
| where timestamp > ago(30d)
| where name == "ConversationClosed"
| summarize
    total = count(),
    escalated = countif(customDimensions.status == "escalated")
| extend escalation_rate = round(todouble(escalated) / todouble(total) * 100, 1)
| project escalation_rate
```
**Visualization:** Single stat (green < 30%, red ≥ 30%)

#### 3.3 Satisfaction Score — 30-Day (stat)
```kql
customEvents
| where timestamp > ago(30d)
| where name == "FeedbackSubmitted"
| summarize
    total = count(),
    positive = countif(customDimensions.rating == "positive")
| extend satisfaction_pct = round(todouble(positive) / todouble(total) * 100, 1)
| project satisfaction_pct
```
**Visualization:** Single stat (green ≥ 80%, yellow 70–80%, red < 70%)

#### 3.4 Query Volume — Daily Trend (time chart)
```kql
customEvents
| where timestamp > ago(30d)
| where name == "ChatResponse"
| summarize query_count = count() by bin(timestamp, 1d)
| render timechart
```
**Visualization:** Bar chart

#### 3.5 Top 20 Intents (bar chart)
```kql
customEvents
| where timestamp > ago(7d)
| where name == "ChatResponse"
| where isnotempty(customDimensions.intent)
| summarize count() by tostring(customDimensions.intent)
| top 20 by count_
| render barchart
```

#### 3.6 Response Type Distribution (pie chart)
```kql
customEvents
| where timestamp > ago(7d)
| where name == "ChatResponse"
| summarize count() by tostring(customDimensions.response_type)
| render piechart
```

#### 3.7 LLM Fallback Rate — 7-Day (time chart)
```kql
customEvents
| where timestamp > ago(7d)
| where name == "ChatResponse"
| summarize
    total = count(),
    fallback = countif(customDimensions.response_type == "fallback_search")
    by bin(timestamp, 1h)
| extend fallback_rate = todouble(fallback) / todouble(total) * 100
| project timestamp, fallback_rate
| render timechart
```
**Visualization:** Line chart with threshold at 1% (SLO: 99% full RAG)

#### 3.8 Unanswered Query Log (table)
```kql
customEvents
| where timestamp > ago(7d)
| where name == "ChatResponse"
| where customDimensions.response_type == "no_match"
| summarize
    count = count(),
    last_asked = max(timestamp)
    by tostring(customDimensions.query)
| order by count desc
| take 20
```
**Visualization:** Table

---

## Dashboard 4: Infrastructure

**Purpose:** Resource utilization and capacity planning.
**Audience:** Platform Engineering
**Refresh interval:** 5 minutes

### Panels

#### 4.1 CPU Utilization (time chart)
**Source:** Azure Container Apps metric `UsageNanoCores`

#### 4.2 Memory Utilization (time chart)
**Source:** Azure Container Apps metric `WorkingSetBytes`

#### 4.3 PostgreSQL Active Connections (time chart)
**Source:** Azure Database for PostgreSQL metric `active_connections`

#### 4.4 Redis Memory Usage (time chart)
**Source:** Azure Cache for Redis metric `usedmemory`

#### 4.5 Azure AI Search Query Latency (time chart)
```kql
dependencies
| where timestamp > ago(24h)
| where type == "HTTP" and target contains "search"
| summarize p95 = percentile(duration, 95) by bin(timestamp, 5m)
| render timechart
```

#### 4.6 Azure OpenAI Token Usage (time chart)
```kql
dependencies
| where timestamp > ago(24h)
| where type == "HTTP" and target contains "openai"
| summarize request_count = count(), p95_ms = percentile(duration, 95) by bin(timestamp, 1h)
| render timechart
```

#### 4.7 Scaling Events (table)
**Source:** Azure Container Apps system logs filtered for scaling events
