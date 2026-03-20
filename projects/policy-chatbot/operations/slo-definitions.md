# SLO Definitions: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-20
> **Produced by:** Monitor Agent
> **Input:** `projects/policy-chatbot/requirements/requirements.md` (non-functional requirements)

---

## SLO: API Availability

- **Source:** NFR-004 — "99.5% uptime during business hours (7 AM–7 PM local time, Monday–Friday)"
- **Indicator (SLI):** Proportion of HTTP requests that return a non-5xx status code
- **Target:** 99.5% of requests over a rolling 30-day window return non-5xx responses
- **Error Budget:** 3 hours 36 minutes per 30-day window (0.5% of business hours ≈ 360 business hours/month × 0.005 = 1.8h; measured against all hours: 30d × 24h × 0.005 = 3.6h)
- **Measurement (KQL):**
  ```kql
  requests
  | where timestamp > ago(30d)
  | where name !in ("/health", "/ready")
  | summarize total = count(), errors = countif(resultCode startswith "5")
  | extend availability = 1.0 - (todouble(errors) / todouble(total))
  ```
- **Alert Policy:**
  - Fast burn (error rate > 1% for 5min → budget burning at >2x rate) → **Page on-call**
  - Slow burn (error rate > 0.5% for 1h → budget burning at >1x rate) → **Create ticket**

---

## SLO: Chat Response Latency

- **Source:** NFR-001 — "Return an initial response within 5 seconds for 95% of queries under normal load"
- **Indicator (SLI):** p95 response time for `/v1/chat` endpoint
- **Target:** p95 < 5000ms for 95% of 5-minute windows in a 30-day period
- **Measurement (KQL):**
  ```kql
  requests
  | where timestamp > ago(5m)
  | where name startswith "/v1/chat"
  | summarize p95_ms = percentile(duration, 95)
  ```
- **Alert Policy:**
  - p95 > 5000ms for 3 consecutive 5-minute windows (15 min) → **Page on-call**
  - p95 > 4000ms for 3 consecutive 5-minute windows (early warning) → **Create ticket**

---

## SLO: Non-Chat API Latency

- **Source:** NFR-001 (general performance expectation for non-LLM endpoints)
- **Indicator (SLI):** p99 response time for all non-chat, non-health endpoints
- **Target:** p99 < 1000ms for 95% of 5-minute windows in a 30-day period
- **Measurement (KQL):**
  ```kql
  requests
  | where timestamp > ago(5m)
  | where name !in ("/health", "/ready")
  | where name !startswith "/v1/chat"
  | summarize p99_ms = percentile(duration, 99)
  ```
- **Alert Policy:**
  - p99 > 1000ms for 3 consecutive windows → **Create ticket**

---

## SLO: Document Indexing Duration

- **Source:** NFR-002 — "Single document re-indexing (up to 200 pages) SHALL complete within 5 minutes"
- **Source:** NFR-003 — "Full corpus re-indexing (~140 documents, ~8,000 pages) SHALL complete within 2 hours"
- **Indicator (SLI):** Duration of document indexing jobs
- **Target:** 99% of single-document indexing jobs complete within 5 minutes
- **Measurement (KQL):**
  ```kql
  customMetrics
  | where name == "document_indexing_duration_seconds"
  | where timestamp > ago(30d)
  | summarize
      total_jobs = count(),
      within_slo = countif(value <= 300)
  | extend compliance = todouble(within_slo) / todouble(total_jobs)
  ```
- **Alert Policy:**
  - Single document indexing exceeds 5 minutes → **Create ticket**
  - Full corpus indexing exceeds 2 hours → **Page on-call**

---

## SLO: LLM Dependency Availability

- **Source:** NFR-006 — "If the LLM service is unavailable, the system SHALL fall back to keyword-based search"
- **Indicator (SLI):** Proportion of Azure OpenAI API calls that succeed (non-5xx)
- **Target:** 99.0% of LLM calls succeed over a rolling 7-day window
- **Measurement (KQL):**
  ```kql
  dependencies
  | where timestamp > ago(7d)
  | where target contains "openai"
  | summarize total = count(), failures = countif(success == false)
  | extend llm_availability = 1.0 - (todouble(failures) / todouble(total))
  ```
- **Alert Policy:**
  - LLM failure rate > 10% for 5 minutes → **Page on-call** (fallback mode triggers)
  - LLM failure rate > 5% for 15 minutes → **Create ticket**

---

## SLO: Concurrent Capacity

- **Source:** NFR-010 — "Support at least 200 concurrent conversations without degradation"
- **Source:** NFR-013 — "Handle 3x increase (600 concurrent) without architectural changes"
- **Indicator (SLI):** Active concurrent connections / request queue depth
- **Target:** No request queuing or error rate increase when concurrent conversations ≤ 200
- **Measurement (KQL):**
  ```kql
  performanceCounters
  | where timestamp > ago(5m)
  | where name == "Active Requests"
  | summarize max_concurrent = max(value)
  ```
- **Alert Policy:**
  - Active requests > 150 (75% of 200 capacity) → **Create ticket** (scaling warning)
  - Active requests > 200 → **Page on-call**

---

## Error Budget Policy

| Budget Remaining | Action |
|-----------------|--------|
| > 50% | Normal development velocity; deploy freely |
| 25–50% | Increase review rigor; no risky deployments without rollback plan |
| < 25% | Feature freeze; reliability work only |
| 0% (exhausted) | All hands on reliability until budget recovers |

---

## Review Cadence

- **Weekly:** SLO dashboard review in engineering standup
- **Monthly:** Error budget report to engineering leadership and HR Service Desk Manager
- **Quarterly:** SLO target review and adjustment based on user feedback data (FR-028, FR-029)
