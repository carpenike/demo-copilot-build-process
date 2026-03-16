# SLO Definitions: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-16
> **Produced by:** Monitor Agent
> **Input:** `projects/policy-chatbot/requirements/requirements.md` (non-functional requirements)

---

## SLO: API Availability

- **Indicator (SLI):** Proportion of HTTP requests that return a non-5xx status code
- **Target:** 99.5% of requests over a rolling 30-day window
- **Source NFR:** NFR-004 — "99.5% uptime during business hours (7 AM – 7 PM, Mon–Fri)"
- **Error Budget:** 3.6 hours/month (216 minutes)
- **Measurement (KQL):**
  ```kql
  requests
  | where timestamp > ago(30d)
  | where name !in ("/health", "/ready")
  | summarize total = count(), errors = countif(resultCode startswith "5")
  | extend availability = 1.0 - (todouble(errors) / todouble(total))
  ```
- **Alert Policy:**
  - Fast burn (> 2x budget rate for 5 min) → **Page on-call** (alert: `SLOBurnRateFast`)
  - Slow burn (> 1x budget rate for 1h) → **Create ticket** (alert: `SLOBurnRateSlow`)

---

## SLO: API Latency

- **Indicator (SLI):** p95 response time for non-health-check endpoints
- **Target:** p95 < 5000ms for 95% of 5-minute windows in a 30-day period
- **Source NFR:** NFR-001 — "Return initial response within 5 seconds for 95% of queries under normal load"
- **Measurement (KQL):**
  ```kql
  requests
  | where timestamp > ago(5m)
  | where name !in ("/health", "/ready")
  | summarize p95_ms = percentile(duration, 95)
  ```
- **Alert Policy:**
  - p95 > 5000ms for 3 consecutive 5-minute windows → **Page on-call** (alert: `HighLatency`)

---

## SLO: LLM Availability

- **Indicator (SLI):** Proportion of chat requests that receive a full RAG response (not fallback)
- **Target:** 99% of chat requests use full RAG (not keyword fallback) over a 7-day window
- **Source NFR:** NFR-006 — "If LLM unavailable, fall back to keyword search"
- **Measurement (KQL):**
  ```kql
  customEvents
  | where timestamp > ago(7d)
  | where name == "ChatResponse"
  | summarize
      total = count(),
      fallback = countif(customDimensions.response_type == "fallback_search")
  | extend llm_availability = 1.0 - (todouble(fallback) / todouble(total))
  ```
- **Alert Policy:**
  - Fallback mode triggered > 5 times in 10 minutes → **Page on-call** (alert: `LLMUnavailable`)

---

## SLO: Resolution Rate

- **Indicator (SLI):** Proportion of conversations resolved without escalation
- **Target:** ≥ 70% of conversations resolved without human escalation over a 30-day window
- **Source:** Business objective — "Self-service resolution of at least 70% of policy inquiries"
- **Measurement (KQL):**
  ```kql
  customEvents
  | where timestamp > ago(30d)
  | where name == "ConversationClosed"
  | summarize
      total = count(),
      escalated = countif(customDimensions.status == "escalated")
  | extend resolution_rate = 1.0 - (todouble(escalated) / todouble(total))
  ```
- **Alert Policy:**
  - Escalation rate > 30% for 24 hours → **Create ticket** (alert: `HighEscalationRate`)

---

## SLO: Answer Quality

- **Indicator (SLI):** Ratio of positive to total feedback responses
- **Target:** ≥ 80% positive feedback ("helpful" or "very helpful") over a 30-day window
- **Source:** Business objective — "80%+ employee satisfaction rating by Q4 2026"
- **Measurement (KQL):**
  ```kql
  customEvents
  | where timestamp > ago(30d)
  | where name == "FeedbackSubmitted"
  | summarize
      total = count(),
      positive = countif(customDimensions.rating == "positive")
  | extend satisfaction_rate = todouble(positive) / todouble(total)
  ```
- **Alert Policy:**
  - Satisfaction drops below 70% over a 7-day rolling window → **Create ticket**

---

## Error Budget Policy

| Budget Remaining | Action |
|-----------------|--------|
| > 50% | Normal development velocity |
| 25–50% | Increase review rigor; no risky deployments |
| < 25% | Feature freeze; reliability work only |
| 0% (exhausted) | All hands on reliability until budget recovers |

---

## Review Cadence

- **Weekly:** SLO dashboard review in engineering standup
- **Monthly:** Error budget report to Platform Engineering lead + VP Employee Experience
- **Quarterly:** SLO target review and adjustment based on actual usage patterns
