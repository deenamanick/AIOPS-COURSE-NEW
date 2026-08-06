# Module 9: Predictive Maintenance & Capacity Planning

Welcome to Module 9! In Module 8, you parsed logs, correlated alerts into incidents, and traced cascading failures to their root cause. Correlation tells you **why** something broke after it broke. This module teaches you to predict **when** something will break before it does—and act in time to prevent it.

---

## Learning Objectives

By the end of this module, you will be able to:

1. Fit a **linear regression** model to historical disk, CPU, and memory time-series data and forecast when each will reach capacity.
2. Build an **infrastructure risk score** engine that produces a weighted composite score with Green/Yellow/Red severity.
3. Calculate the four **DORA metrics** (Deployment Frequency, Lead Time, Change Failure Rate, MTTR) from real GitHub Actions data.
4. Set **predictive alerts** that fire hours or days before an actual failure.
5. Distinguish predictive operations from reactive firefighting and articulate the business value of each.

---

## Prerequisites

- ✅ Module 8 completed
- ✅ Python 3.10+ with `pip` available
- ✅ Docker Engine and Docker Compose v2 installed
- ✅ Familiarity with basic statistics (mean, slope, intercept)
- ✅ `matplotlib` and `scikit-learn` installed (lab installs them automatically)
- ✅ At least 4 GB RAM available

---

## Lab Architecture

```text
Historical CSV Data ──► Forecasting Engine ──► Predicted Exhaustion Date
(disk, CPU, memory)            │                        │
                               ▼                        ▼
                        matplotlib plots         Predictive Alert
                                                 (fires 2h before)

Live Metrics ──► Risk Score Engine ──► Composite Score (0–100)
(CPU, mem, disk, errors)                    │
                                   ┌────────┴────────┐
                                   ▼        ▼        ▼
                                 Green    Yellow     Red
                                (< 40)   (40–70)   (> 70)

GitHub Actions ──► DORA Calculator ──► DORA Dashboard
(workflow runs)                         (4 metrics + tier)
```

---

## Lab Setup

```bash
cd Module-9/lab
pip install -r requirements.txt
docker compose up -d --build
```

Open:

- Risk score dashboard: `http://localhost:8080`
- Flask metrics: `http://localhost:5000/metrics`
- Forecast outputs: `lab/output/` (generated plots)

---

## Lessons in this Module

| # | Lesson | What You'll Do |
|---|---|---|
| 01 | [Predictive vs Reactive Operations](./01-predictive-vs-reactive.md) | Understand why forecasting prevents outages and learn the core concepts |
| 02 | [Time-Series Forecasting](./02-time-series-forecasting.md) | Fit linear regression to disk/CPU/memory data and predict exhaustion dates |
| 03 | [Infrastructure Risk Scoring](./03-risk-scoring.md) | Build a weighted composite risk engine with Green/Yellow/Red severity |
| 04 | [DORA Metrics & Engineering Performance](./04-dora-metrics.md) | Calculate Deployment Frequency, Lead Time, Change Failure Rate, and MTTR |
| 05 | [Break/Fix: Predictive Alerting](./05-break-fix-predictive.md) | Inject a disk growth pattern, forecast the failure, and alert before it happens |
| 06 | [Production Patterns & Deliverables](./06-bonus-deliverables.md) | Learn advanced forecasting, governance, and submit evidence |

Start with **01-predictive-vs-reactive.md**.
