# Dashboard Spec: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-20
> **Produced by:** Monitor Agent
> **Platform:** Azure Monitor Workbooks (backed by Application Insights + Log Analytics)

---

## Overview

This dashboard provides operational visibility into the Policy Chatbot service.
It is organized into five sections aligned with the RED method (Rate, Errors,
Duration) plus saturation and business metrics. All queries use KQL against
Application Insights and Log Analytics data sources.

**Workbook name:** `policy-chatbot-operations`
**Data source:** Application Insights instance `{prefix}-insights`
**Refresh interval:** Auto-refresh every 5 minutes
**Time range selector:** Default 24 hours; options: 1h, 6h, 24h, 7d, 30d

---

## Section 1: Service Health Overview

**Layout:** Single row of KPI tiles across the top

### Tile 1.1: Current Availability (%)
```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| summarize total = count(), errors = countif(resultCode startswith "5")
| extend availability = round(100.0 * (1.0 - todouble(errors) / todouble(total)), 2)
| project availability
```
**Visualization:** Single value tile
**Thresholds:** Green ≥ 99.5%, Yellow ≥ 99.0%, Red < 99.0%
**SLO reference:** 99.5% (NFR-004)

### Tile 1.2: 30-Day Error Budget Remaining
```kql
let slo_target = 0.995;
let budget_total_minutes = 30.0 * 24 * 60 * (1.0 - slo_target);
requests
| where timestamp > ago(30d)
| where name !in ("/health", "/ready")
| summarize total = count(), errors = countif(resultCode startswith "5")
| extend error_rate = todouble(errors) / todouble(total)
| extend budget_consumed_minutes = 30.0 * 24 * 60 * error_rate
| extend budget_remaining_pct = round(100.0 * (1.0 - budget_consumed_minutes / budget_total_minutes), 1)
| project budget_remaining_pct
```
**Visualization:** Single value tile
**Thresholds:** Green > 50%, Yellow 25-50%, Red < 25%

### Tile 1.3: Active Alerts Count
```kql
AlertsManagementResources
| where properties.essentials.targetResourceType == "microsoft.insights/components"
| where properties.essentials.alertState == "New" or properties.essentials.alertState == "Acknowledged"
| summarize active_alerts = count()
```
**Visualization:** Single value tile
**Thresholds:** Green = 0, Yellow = 1-2, Red ≥ 3

### Tile 1.4: Healthy Replicas
```kql
ContainerAppSystemLogs_CL
| where ContainerAppName_s contains "policy-chatbot"
| where timestamp > ago(5m)
| summarize replica_count = dcount(RevisionName_s)
```
**Visualization:** Single value tile
**Thresholds:** Green ≥ 2, Yellow = 1, Red = 0

---

## Section 2: Error Rate & Availability

### Chart 2.1: Error Rate Over Time
```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| summarize
    total = count(),
    errors_5xx = countif(resultCode startswith "5"),
    errors_4xx = countif(resultCode startswith "4")
    by bin(timestamp, 5m)
| extend error_rate_5xx = round(100.0 * todouble(errors_5xx) / todouble(total), 2)
| extend error_rate_4xx = round(100.0 * todouble(errors_4xx) / todouble(total), 2)
| project timestamp, error_rate_5xx, error_rate_4xx
```
**Visualization:** Line chart (dual axis)
**Annotations:** Horizontal line at 0.5% (SLO threshold from NFR-004)

### Chart 2.2: Error Breakdown by Endpoint
```kql
requests
| where timestamp > ago(24h)
| where resultCode startswith "5"
| summarize error_count = count() by name, resultCode
| order by error_count desc
| take 20
```
**Visualization:** Stacked bar chart

### Chart 2.3: HTTP Status Code Distribution
```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| summarize count() by resultCode
| order by count_ desc
```
**Visualization:** Pie chart

---

## Section 3: Latency

### Chart 3.1: Chat Endpoint Latency Percentiles
```kql
requests
| where timestamp > ago(24h)
| where name startswith "/v1/chat"
| summarize
    p50 = percentile(duration, 50),
    p95 = percentile(duration, 95),
    p99 = percentile(duration, 99)
    by bin(timestamp, 5m)
```
**Visualization:** Line chart (3 series: p50, p95, p99)
**Annotations:** Horizontal line at 5000ms (SLO threshold from NFR-001)

### Chart 3.2: Non-Chat API Latency Percentiles
```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| where name !startswith "/v1/chat"
| summarize
    p50 = percentile(duration, 50),
    p95 = percentile(duration, 95),
    p99 = percentile(duration, 99)
    by bin(timestamp, 5m)
```
**Visualization:** Line chart (3 series)
**Annotations:** Horizontal line at 1000ms (p99 target)

### Chart 3.3: Dependency Latency
```kql
dependencies
| where timestamp > ago(24h)
| summarize
    p95_latency = percentile(duration, 95)
    by bin(timestamp, 15m), target
| order by timestamp desc
```
**Visualization:** Line chart (series per dependency: openai, postgres, redis, search)

### Chart 3.4: Slowest Endpoints (Last 24h)
```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| summarize
    p95 = percentile(duration, 95),
    count = count()
    by name
| order by p95 desc
| take 10
```
**Visualization:** Table

---

## Section 4: Throughput & Saturation

### Chart 4.1: Request Rate Over Time
```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| summarize request_count = count() by bin(timestamp, 5m)
```
**Visualization:** Area chart
**Annotations:** Horizontal line at estimated capacity threshold

### Chart 4.2: Request Rate by Endpoint
```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| summarize count() by bin(timestamp, 1h), name
```
**Visualization:** Stacked area chart

### Chart 4.3: Concurrent Request Estimate
```kql
requests
| where timestamp > ago(24h)
| summarize concurrent = dcount(id) by bin(timestamp, 1s)
| summarize
    max_concurrent = max(concurrent),
    avg_concurrent = avg(concurrent)
    by bin(timestamp, 5m)
```
**Visualization:** Line chart (2 series)
**Annotations:** Horizontal lines at 150 (warning) and 200 (capacity limit, NFR-010/013)

### Chart 4.4: Memory & CPU Usage
```kql
performanceCounters
| where timestamp > ago(24h)
| where category == "Process"
| where name in ("% Processor Time", "Private Bytes")
| summarize avg_value = avg(value) by bin(timestamp, 5m), name
```
**Visualization:** Dual-axis line chart (CPU %, Memory bytes)

---

## Section 5: Dependency Health

### Chart 5.1: Dependency Success Rate
```kql
dependencies
| where timestamp > ago(24h)
| summarize
    total = count(),
    successes = countif(success == true)
    by bin(timestamp, 15m), target
| extend success_rate = round(100.0 * todouble(successes) / todouble(total), 1)
| project timestamp, target, success_rate
```
**Visualization:** Line chart (series per dependency)

### Chart 5.2: Dependency Call Volume
```kql
dependencies
| where timestamp > ago(24h)
| summarize call_count = count() by bin(timestamp, 15m), target
```
**Visualization:** Stacked area chart

### Chart 5.3: Azure OpenAI Token Usage
```kql
customMetrics
| where timestamp > ago(24h)
| where name in ("openai_prompt_tokens", "openai_completion_tokens")
| summarize total_tokens = sum(value) by bin(timestamp, 1h), name
```
**Visualization:** Stacked bar chart

---

## Section 6: Business Metrics

### Chart 6.1: Chat Conversations Per Hour
```kql
requests
| where timestamp > ago(7d)
| where name == "/v1/chat"
| extend conversation_id = tostring(customDimensions.conversation_id)
| summarize conversations = dcount(conversation_id) by bin(timestamp, 1h)
```
**Visualization:** Bar chart

### Chart 6.2: Response Type Distribution
```kql
requests
| where timestamp > ago(24h)
| where name startswith "/v1/chat"
| where resultCode == "200"
| extend response_type = tostring(customDimensions.response_type)
| summarize count() by response_type
```
**Visualization:** Pie chart (answer, checklist, no_match, fallback_search, confidential_escalation, escalation_offer)

### Chart 6.3: Escalation Rate
```kql
let total_chats = requests
| where timestamp > ago(7d)
| where name startswith "/v1/chat"
| summarize total = count();
let escalations = requests
| where timestamp > ago(7d)
| where name == "/v1/chat/escalate"
| summarize escalated = count();
total_chats | join escalations on $left.total == $left.total
| extend escalation_rate_pct = round(100.0 * todouble(escalated) / todouble(total), 2)
```
**Visualization:** Single value tile + trend line over 7d

### Chart 6.4: Feedback Score
```kql
requests
| where timestamp > ago(7d)
| where name == "/v1/feedback"
| extend rating = tostring(customDimensions.rating)
| summarize
    positive = countif(rating == "positive"),
    negative = countif(rating == "negative")
    by bin(timestamp, 1d)
| extend satisfaction_pct = round(100.0 * todouble(positive) / todouble(positive + negative), 1)
```
**Visualization:** Combo chart (bars for positive/negative counts, line for satisfaction %)

### Chart 6.5: Top Unanswered Queries
```kql
requests
| where timestamp > ago(7d)
| where name startswith "/v1/chat"
| where resultCode == "200"
| extend response_type = tostring(customDimensions.response_type)
| where response_type == "no_match"
| extend query_text = tostring(customDimensions.query_preview)
| summarize count() by query_text
| order by count_ desc
| take 20
```
**Visualization:** Table

---

## Access & Permissions

- **Viewers:** Platform Engineering, HR Service Desk Manager
- **Editors:** Platform Engineering on-call rotation
- **Data source RBAC:** Log Analytics Reader role on `{prefix}-logs` workspace
