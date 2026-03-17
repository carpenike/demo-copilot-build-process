# SLO Definitions: Policy Chatbot

> **Version:** 1.0
> **Date:** 2026-03-17
> **Produced by:** Monitor Agent
> **Input:** `projects/policy-chatbot/requirements/requirements.md` (NFR-001–NFR-018)

---

## SLO: API Availability

- **Indicator (SLI):** Proportion of HTTP requests that return a non-5xx status code
- **Target:** 99.5% of requests over a rolling 30-day window during business hours (7 AM – 7 PM Mon–Fri)
- **Source NFR:** NFR-004 — "99.5% uptime during business hours"
- **Error Budget:** 3.6 hours/month (216 minutes)
- **Measurement (KQL):**
  ```kql
  requests
  | where timestamp > ago(30d)
  | where name !in ("/health", "/ready")
  | summarize total = count(), errors = countif(resultCode startswith "5")
  | extend availability = 1.0 - (todouble(errors) / todouble(total))
  | extend budget_remaining_pct = (availability - 0.995) / (1.0 - 0.995) * 100
  ```
- **Error Budget Burn Rate (KQL):**
  ```kql
  let slo_target = 0.995;
  let window = 30d;
  let budget_total = (1.0 - slo_target) * totimespan(window) / 1m; // 216 minutes
  requests
  | where timestamp > ago(1h)
  | where name !in ("/health", "/ready")
  | summarize total = count(), errors = countif(resultCode startswith "5")
  | extend hourly_error_rate = todouble(errors) / todouble(total)
  | extend burn_rate = hourly_error_rate / (1.0 - slo_target)
  ```
- **Alert Policy:**
  - Fast burn (burn rate > 14.4x for 5 min) → **Page on-call** (exhausts budget in 1 hour)
  - Slow burn (burn rate > 1x for 1 hour) → **Create ticket**
  - Budget < 25% remaining → **Notify service owner**

---

## SLO: API Latency

- **Indicator (SLI):** p95 response time for non-health-check endpoints
- **Target:** p95 < 5000ms for 95% of 5-minute windows in a 30-day period
- **Source NFR:** NFR-001 — "return an initial response within 5 seconds for 95% of queries"
- **Measurement (KQL):**
  ```kql
  requests
  | where timestamp > ago(5m)
  | where name !in ("/health", "/ready")
  | summarize p95_ms = percentile(duration, 95), p99_ms = percentile(duration, 99)
  ```
- **Alert Policy:**
  - p95 > 5000ms for 3 consecutive 5-minute windows → **Page on-call**
  - p95 > 4000ms for 15 minutes → **Create ticket** (approaching threshold)

---

## SLO: LLM Dependency Availability

- **Indicator (SLI):** Proportion of Azure OpenAI API calls that succeed (non-5xx, non-429)
- **Target:** 99.0% of LLM calls succeed over a rolling 24-hour window
- **Source NFR:** NFR-006 — "fall back to keyword-based search" when LLM unavailable
- **Measurement (KQL):**
  ```kql
  dependencies
  | where timestamp > ago(24h)
  | where type == "HTTP" and target contains "openai"
  | summarize total = count(), failures = countif(resultCode startswith "5" or resultCode == "429")
  | extend success_rate = 1.0 - (todouble(failures) / todouble(total))
  ```
- **Alert Policy:**
  - Success rate < 95% for 10 minutes → **Page on-call** (LLM degraded, fallback active)
  - Any 5-minute window with 100% failure → **Page on-call** (LLM down)

---

## SLO: Chat Resolution Rate

- **Indicator (SLI):** Proportion of conversations resolved without escalation to a live agent
- **Target:** ≥ 70% of conversations resolved without human escalation
- **Source NFR:** Business objective — "self-service resolution of at least 70% of policy inquiries"
- **Measurement (KQL):**
  ```kql
  customEvents
  | where timestamp > ago(7d)
  | where name == "analytics_event"
  | where customDimensions.event_type in ("query", "escalation")
  | summarize
      total_queries = countif(customDimensions.event_type == "query"),
      escalations = countif(customDimensions.event_type == "escalation")
  | extend resolution_rate = 1.0 - (todouble(escalations) / todouble(total_queries))
  ```
- **Alert Policy:**
  - Resolution rate < 70% over a rolling 24-hour window → **Create ticket**
  - Resolution rate < 50% for 4 hours → **Notify service owner**

---

## Error Budget Policy

### Budget Exhaustion Rules

| Budget Remaining | Action |
|-----------------|--------|
| > 50% | Normal operations — deploy at will |
| 25–50% | Caution — only deploy bug fixes and reliability improvements |
| 10–25% | Freeze non-essential deployments; focus on reliability |
| < 10% | Feature freeze; all engineering effort on reliability |
| 0% (exhausted) | Full freeze until budget regenerates; post-incident review required |

### Budget Reset

Error budgets are calculated on a rolling 30-day window. Budget naturally
regenerates as old errors age out of the window.

### Exemptions

The following events do not count against the error budget:
- Planned maintenance windows (announced ≥ 48 hours in advance)
- Azure platform outages (confirmed via Azure Status page)
- Load test traffic (identified by `X-Load-Test: true` header)
