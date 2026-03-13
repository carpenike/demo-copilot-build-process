# SLO Definitions: [Service Name]

> **Version:** 1.0
> **Date:** YYYY-MM-DD
> **Produced by:** Monitor Agent
> **Input:** `projects/<project>/requirements/requirements.md` (non-functional requirements)

---

## SLO: API Availability

- **Indicator (SLI):** Proportion of HTTP requests that return a non-5xx status code
- **Target:** [99.9%] of requests over a rolling 30-day window
- **Error Budget:** [43.2 minutes/month]
- **Measurement:** `1 - (sum 5xx responses / sum all responses)` over 30 days
- **Alert Policy:**
  - Fast burn (> 2x budget rate for 5min) → **Page on-call**
  - Slow burn (> 1x budget rate for 1h) → **Create ticket**

---

## SLO: API Latency

- **Indicator (SLI):** p99 response time for non-health-check endpoints
- **Target:** p99 < [X]ms for [95%] of 5-minute windows in a 30-day period
- **Measurement:** `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))`
- **Alert Policy:**
  - p99 > threshold for 3 consecutive 5-minute windows → **Page on-call**

---

## SLO: Data Freshness (if applicable)

- **Indicator (SLI):** Age of the most recent successfully processed record
- **Target:** Data no older than [N] minutes during business hours
- **Measurement:** `current_time - last_successful_sync_timestamp`
- **Alert Policy:**
  - Freshness > threshold for 10 minutes → **Create ticket**

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
- **Monthly:** Error budget report to engineering leadership
- **Quarterly:** SLO target review and adjustment
