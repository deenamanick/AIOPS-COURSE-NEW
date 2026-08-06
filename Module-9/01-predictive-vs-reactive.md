# 01 — Predictive vs Reactive Operations

Every outage follows the same pattern: a resource exhausts, a service fails, an alert fires, a human responds. The time between failure and response is **Mean Time to Recover (MTTR)**. Predictive operations insert a new step before the failure: **forecasting**. If you know the disk will fill in 14 days, you act on day 10, and the outage never happens.

---

## The Reactive Timeline

```text
Day 1–29:  Disk usage grows silently
Day 30:    Disk hits 100% → writes fail → database crashes → 5xx errors
Day 30:    Alert fires (reactive) → on-call paged → scramble to free space
Day 30:    MTTR = 45 minutes of user impact
```

## The Predictive Timeline

```text
Day 1–15:  Disk usage grows, forecasting model tracks the trend
Day 16:    Forecast: "Disk will reach 100% on Day 30"
Day 16:    Predictive alert fires → ticket created → capacity expanded
Day 30:    Nothing happens. Users never notice.
```

The business difference is stark: zero user impact, zero pages, zero incident reports.

---

## Core Concepts

### Time-Series Data

A time series is a sequence of measurements ordered by time. Infrastructure metrics are natural time series:

| Timestamp | Disk Used (%) |
|---|---|
| 2026-07-01 | 42.1 |
| 2026-07-02 | 42.8 |
| 2026-07-03 | 43.5 |
| ... | ... |
| 2026-07-30 | 63.2 |

The question is not "what is the disk usage now?" (monitoring answers that). The question is **"when will it reach 100%?"** (forecasting answers that).

### Forecasting Models

| Model | Complexity | Best For |
|---|---|---|
| Moving average | Low | Smoothing noise, short-term trend |
| Linear regression | Low | Steady growth patterns (disk, user count) |
| ARIMA | Medium | Seasonal patterns (traffic, CPU by hour) |
| Prophet (Facebook) | Medium | Business metrics with holidays and seasonality |
| LSTM / Neural nets | High | Complex multi-variate patterns (rarely needed for infra) |

This module focuses on **linear regression** because it handles the most common infrastructure forecasting problem—steady resource growth—with minimal complexity and maximum interpretability.

---

## What You Will Forecast

| Metric | Question |
|---|---|
| Disk usage | When will the filesystem reach 100%? |
| CPU utilization | When will sustained CPU exceed 90%? |
| Memory usage | When will the system start swapping? |
| Error rate trend | Is the error rate growing over time? |

### Capacity Planning Formula

```text
days_remaining = (capacity_limit - current_value) / daily_growth_rate
exhaustion_date = today + days_remaining
```

For disk:

```text
current: 63%
limit: 100%
daily growth: 0.7%/day
days remaining: (100 - 63) / 0.7 = 52.8 days
exhaustion: today + 53 days
```

---

## Risk Scoring

A single metric tells you one thing. A **composite risk score** tells you how close the entire system is to trouble:

```text
risk_score = (CPU × 0.2) + (memory × 0.2) + (disk × 0.3) + (error_rate × 0.3)
```

| Score | Severity | Action |
|---|---|---|
| 0–39 | 🟢 Green | Normal operations |
| 40–70 | 🟡 Yellow | Review and plan capacity |
| 71–100 | 🔴 Red | Immediate action required |

The weights reflect impact: disk and error rate directly cause outages; CPU and memory degrade performance but rarely cause immediate failures.

---

## DORA Metrics

The DevOps Research and Assessment (DORA) team identified four metrics that predict software delivery performance:

| Metric | What It Measures | Elite Benchmark |
|---|---|---|
| Deployment Frequency | How often code reaches production | Multiple times per day |
| Lead Time for Changes | Commit to production duration | Less than 1 hour |
| Change Failure Rate | % of deployments causing failures | 0–15% |
| MTTR | Time to restore service after failure | Less than 1 hour |

These are not vanity metrics. They correlate with organizational performance, employee satisfaction, and customer outcomes. You will calculate them from your own CI/CD data in this module.

---

## Lab Preview

In the following lessons, you will:

1. Load 30 days of CSV data and fit a linear regression model.
2. Plot actual vs predicted values and annotate the predicted exhaustion date.
3. Build a risk score engine that combines four metrics into one severity.
4. Calculate DORA metrics from GitHub Actions workflow runs.
5. Inject a disk growth pattern and verify your forecast matches reality.

---

## Key Takeaway

Reactive operations are expensive. Every outage costs user trust, engineering time, and revenue. Predictive operations are cheap by comparison: a Python script, a CSV, and a linear model can prevent the next cascading failure you traced in Module 8.

In the next lesson, you will build the forecasting engine.
