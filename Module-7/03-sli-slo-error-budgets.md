# 03 — SLIs, SLOs, SLAs & Error Budgets

Reliability becomes actionable when it is expressed as a measurable indicator, a target, and a policy.

---

## Definitions

| Term | Meaning | Flask example |
|---|---|---|
| SLI | What is measured | Successful requests ÷ valid requests |
| SLO | Internal reliability target | 99.5% availability over 30 days |
| SLA | External commitment and consequences | 99.0% monthly availability with service credits |

An SLA is not simply a stricter SLO. It is a business agreement with defined measurement scope, exclusions, and consequences. Teams normally keep the internal SLO tighter than the external SLA.

---

## Availability SLI

```promql
1 - (
  sum(rate(http_requests_total{status=~"5.."}[30d]))
  / clamp_min(sum(rate(http_requests_total[30d])), 0.001)
)
```

Display as a percentage by multiplying by 100. Document whether health checks, client errors, maintenance windows, and retries count as valid events.

## Latency SLI

P99 request duration:

```promql
histogram_quantile(
  0.99,
  sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
)
```

A threshold-based latency SLI is often better for an SLO because it describes the fraction of requests meeting a goal. Histograms must include a bucket at the target boundary to calculate it accurately.

---

## Calculate the Error Budget

For a 99.5% availability SLO:

```text
Error budget = 100% - 99.5% = 0.5%
30 days × 24 hours × 60 minutes = 43,200 minutes
43,200 × 0.005 = 216 minutes
```

The service may therefore consume up to **216 minutes of equivalent total unavailability** in the 30-day window. For request-based SLIs, it can fail 0.5% of eligible requests; this is not always identical to wall-clock downtime.

### Budget Remaining

```text
allowed bad events = total eligible events × (1 - SLO)
budget remaining = allowed bad events - observed bad events
budget remaining % = budget remaining / allowed bad events × 100
```

Example: 1,000,000 eligible requests permit 5,000 failures. If 3,500 fail, 1,500 failures—or 30% of the budget—remain.

---

## Error-Budget Policy

| Budget state | Recommended action |
|---|---|
| More than 50% remains | Normal delivery with standard review |
| 25–50% remains | Review risky launches and recurring failures |
| 0–25% remains | Prioritize reliability and require release approval |
| Exhausted | Freeze nonessential releases; restore reliability |

The policy is agreed before an incident. Error budgets are decision tools, not permission to intentionally create outages.

---

## Lab Worksheet

Define:

1. Service and users.
2. Eligible events.
3. Good-event criteria.
4. Measurement source.
5. SLO target and window.
6. Exclusions.
7. Error-budget policy owner.

Then query the lab's short-window recording rules:

```promql
slo:availability:ratio_5m
```

```promql
slo:error_budget_remaining:ratio_5m
```

These five-minute rules are for quick training feedback only. Production policy uses the documented 30-day window.
