# Dashboard Spec: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-17
> **Produced by:** Monitor Agent
> **Tool:** Azure Monitor Workbooks (backed by Application Insights + Log Analytics)

---

## Dashboard Overview

The Policy Chatbot operations dashboard provides real-time visibility into
service health, SLO status, and business metrics. It is built using Azure
Monitor Workbooks backed by KQL queries against Application Insights and
Log Analytics.

**Audience:** On-call engineers, Platform Engineering team, HR Service Desk Manager

**Refresh interval:** Auto-refresh every 5 minutes

---

## Section 1: Service Health (top of dashboard)

### 1.1 Health Status Tiles

| Tile | Query | Visualization | Threshold |
|------|-------|---------------|-----------|
| API Status | `requests \| where timestamp > ago(5m) \| where name == "/health" \| summarize latest = arg_max(timestamp, resultCode) \| project status = iff(resultCode == "200", "Healthy", "Unhealthy")` | Status tile (green/red) | Green = 200, Red = anything else |
| Error Rate (5m) | `requests \| where timestamp > ago(5m) \| where name !in ("/health", "/ready") \| summarize error_rate = round(todouble(countif(resultCode startswith "5")) / todouble(count()) * 100, 2)` | Single value tile | Green < 0.5%, Yellow 0.5–1%, Red > 1% |
| p95 Latency (5m) | `requests \| where timestamp > ago(5m) \| where name !in ("/health", "/ready") \| summarize p95_ms = round(percentile(duration, 95), 0)` | Single value tile | Green < 4000ms, Yellow 4000–5000ms, Red > 5000ms |
| Active Conversations | `customEvents \| where timestamp > ago(30m) \| where name == "analytics_event" \| where customDimensions.event_type == "query" \| summarize dcount(tostring(customDimensions.conversation_id))` | Single value tile | Informational |

### 1.2 SLO Budget Remaining

| Tile | Query | Visualization |
|------|-------|---------------|
| Availability Budget | `requests \| where timestamp > ago(30d) \| where name !in ("/health", "/ready") \| summarize total = count(), errors = countif(resultCode startswith "5") \| extend availability = 1.0 - (todouble(errors) / todouble(total)) \| extend budget_pct = round((availability - 0.995) / (1.0 - 0.995) * 100, 1)` | Gauge (0–100%) |

---

## Section 2: Error Rate & Availability

### 2.1 Error Rate Over Time

```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| summarize
    total = count(),
    errors = countif(resultCode startswith "5")
    by bin(timestamp, 5m)
| extend error_rate_pct = round(todouble(errors) / todouble(total) * 100, 2)
| project timestamp, error_rate_pct
| render timechart
```

**Visualization:** Line chart with SLO threshold line at 0.5%

### 2.2 Errors by Endpoint

```kql
requests
| where timestamp > ago(4h)
| where resultCode startswith "5"
| summarize count() by name, resultCode
| order by count_ desc
| take 20
```

**Visualization:** Bar chart (horizontal)

### 2.3 Error Details

```kql
requests
| where timestamp > ago(1h)
| where resultCode startswith "5"
| project timestamp, name, resultCode, duration, customDimensions
| order by timestamp desc
| take 50
```

**Visualization:** Table (drilldown from error rate chart)

---

## Section 3: Latency

### 3.1 Latency Percentiles Over Time

```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| summarize
    p50 = percentile(duration, 50),
    p95 = percentile(duration, 95),
    p99 = percentile(duration, 99)
    by bin(timestamp, 5m)
| render timechart
```

**Visualization:** Multi-line chart (p50, p95, p99) with SLO threshold line at 5000ms

### 3.2 Latency by Endpoint

```kql
requests
| where timestamp > ago(4h)
| where name !in ("/health", "/ready")
| summarize
    avg_ms = round(avg(duration), 0),
    p95_ms = round(percentile(duration, 95), 0),
    count = count()
    by name
| order by p95_ms desc
```

**Visualization:** Table

---

## Section 4: Throughput

### 4.1 Request Volume Over Time

```kql
requests
| where timestamp > ago(24h)
| where name !in ("/health", "/ready")
| summarize request_count = count() by bin(timestamp, 5m)
| render timechart
```

**Visualization:** Area chart

### 4.2 Requests by Endpoint

```kql
requests
| where timestamp > ago(4h)
| where name !in ("/health", "/ready")
| summarize count() by name
| order by count_ desc
```

**Visualization:** Pie chart

---

## Section 5: Dependencies (Azure OpenAI, AI Search, PostgreSQL, Redis)

### 5.1 Dependency Success Rate Over Time

```kql
dependencies
| where timestamp > ago(24h)
| summarize
    success_rate = round(todouble(countif(success == true)) / todouble(count()) * 100, 2)
    by bin(timestamp, 5m), target
| render timechart
```

**Visualization:** Multi-line chart (one line per dependency)

### 5.2 Dependency Latency

```kql
dependencies
| where timestamp > ago(4h)
| summarize
    avg_ms = round(avg(duration), 0),
    p95_ms = round(percentile(duration, 95), 0),
    calls = count()
    by target
| order by p95_ms desc
```

**Visualization:** Table

### 5.3 Azure OpenAI Throttling (429s)

```kql
dependencies
| where timestamp > ago(24h)
| where target contains "openai"
| where resultCode == "429"
| summarize throttled_count = count() by bin(timestamp, 5m)
| render timechart
```

**Visualization:** Bar chart (highlight throttling spikes)

---

## Section 6: Business Metrics (Chatbot-Specific)

### 6.1 Resolution Rate Over Time

```kql
customEvents
| where timestamp > ago(7d)
| where name == "analytics_event"
| where customDimensions.event_type in ("query", "escalation")
| summarize
    queries = countif(customDimensions.event_type == "query"),
    escalations = countif(customDimensions.event_type == "escalation")
    by bin(timestamp, 1h)
| extend resolution_rate = round((1.0 - todouble(escalations) / todouble(queries)) * 100, 1)
| project timestamp, resolution_rate
| render timechart
```

**Visualization:** Line chart with SLO threshold line at 70%

### 6.2 Top Query Domains

```kql
customEvents
| where timestamp > ago(7d)
| where name == "analytics_event"
| where customDimensions.event_type == "query"
| summarize count() by tostring(customDimensions.intent_domain)
| order by count_ desc
```

**Visualization:** Donut chart

### 6.3 Escalation Reasons

```kql
customEvents
| where timestamp > ago(7d)
| where name == "analytics_event"
| where customDimensions.event_type == "escalation"
| summarize count() by tostring(customDimensions.reason)
| order by count_ desc
```

**Visualization:** Bar chart

### 6.4 Feedback Satisfaction

```kql
customEvents
| where timestamp > ago(7d)
| where name == "analytics_event"
| where customDimensions.event_type == "feedback"
| summarize
    positive = countif(customDimensions.rating == "positive"),
    negative = countif(customDimensions.rating == "negative")
    by bin(timestamp, 1d)
| extend satisfaction_pct = round(todouble(positive) / todouble(positive + negative) * 100, 1)
| render timechart
```

**Visualization:** Line chart with percentage

---

## Section 7: Saturation (Resource Usage)

### 7.1 Container CPU & Memory

```kql
performanceCounters
| where timestamp > ago(24h)
| where category == "Process"
| where counter in ("% Processor Time", "Working Set")
| summarize avg(value) by bin(timestamp, 5m), counter
| render timechart
```

**Visualization:** Dual-axis chart (CPU % left axis, Memory MB right axis)

### 7.2 Active Replica Count

Monitor via Azure Container Apps metrics (not KQL):
- Metric: `Replica Count`
- Aggregation: Average
- Split by: Container App name

**Visualization:** Line chart showing current vs. min/max configured

---

## Workbook Layout

```
┌─────────────────────────────────────────────────────────┐
│  [Health]  [Error %]  [p95 Latency]  [Active Convos]    │  Section 1: Tiles
│  [SLO Budget Gauge]                                     │
├─────────────────────────────────────────────────────────┤
│  Error Rate Over Time          │  Errors by Endpoint    │  Section 2
├─────────────────────────────────────────────────────────┤
│  Latency Percentiles           │  Latency by Endpoint   │  Section 3
├─────────────────────────────────────────────────────────┤
│  Request Volume                │  Requests by Endpoint  │  Section 4
├─────────────────────────────────────────────────────────┤
│  Dependency Success Rate       │  OpenAI Throttling     │  Section 5
├─────────────────────────────────────────────────────────┤
│  Resolution Rate  │  Top Domains  │  Feedback Trend     │  Section 6
├─────────────────────────────────────────────────────────┤
│  CPU & Memory                  │  Replica Count         │  Section 7
└─────────────────────────────────────────────────────────┘
```
