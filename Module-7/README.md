# Module 7: Alerting, SRE & Error Budgets

Welcome to Module 7! In Module 6, you collected metrics and logs, built dashboards, and correlated failures across Prometheus, Grafana, and Loki. Visibility alone does not tell an on-call engineer **when to act**. In this module, you will turn observability signals into actionable alerts, define reliability targets, calculate error budgets, and reduce an alert storm to one root-cause notification.

---

## Learning Objectives

By the end of this module, you will be able to:

1. Configure **Alertmanager** routes, receivers, grouping, inhibition, and silences.
2. Create Prometheus alerts for high CPU, high HTTP error rate, and low disk space.
3. Distinguish **SLIs**, **SLOs**, and **SLAs** for a production service.
4. Calculate remaining **error budget** and apply an error-budget policy.
5. Design symptom-based alerts that reflect user impact.
6. Reduce alert fatigue using severity, ownership, grouping, and inhibition.
7. Document an on-call response with a runbook and escalation path.

---

## Prerequisites

- ✅ Module 6 completed
- ✅ Docker Engine and Docker Compose v2 installed
- ✅ Familiarity with PromQL and Grafana
- ✅ `curl` and a browser available
- ✅ At least 4GB RAM available

---

## Lab Architecture

```text
Node Exporter ─┐
               ├──► Prometheus ── firing alerts ──► Alertmanager
Flask metrics ─┘        │                              │
                       Grafana             group / inhibit / route
                                                       │
                                          ┌────────────┴───────────┐
                                          ▼                        ▼
                                    Mailpit inbox            Webhook log
```

Mailpit safely captures training email at `http://localhost:8025`; no notification leaves the machine. The webhook receiver prints Alertmanager payloads for inspection.

---

## Lab Setup

```bash
cd Module-7/lab
docker compose up -d --build
docker compose ps
```

Open:

- Prometheus: `http://localhost:9090`
- Alertmanager: `http://localhost:9093`
- Mailpit: `http://localhost:8025`
- Webhook receiver: `http://localhost:5001/alerts`
- Flask service: `http://localhost:8080`

---

## Lessons in this Module

| # | Lesson | What You'll Do |
|---|---|---|
| 01 | [Actionable Alerting & Alertmanager](./01-alertmanager-fundamentals.md) | Learn routing, grouping, silencing, severity, and symptom-based alerting |
| 02 | [Prometheus Alert Rules](./02-prometheus-alert-rules.md) | Configure and test HighCPU, HighErrorRate, and DiskAlmostFull |
| 03 | [SLIs, SLOs, SLAs & Error Budgets](./03-sli-slo-error-budgets.md) | Define availability and latency SLIs and calculate a 99.5% error budget |
| 04 | [Alert Fatigue & On-Call Engineering](./04-alert-fatigue-oncall.md) | Reduce a 15-alert database incident using grouping and inhibition |
| 05 | [Break/Fix Activities](./05-break-fix.md) | Consume a lab error budget, apply policy, repair the service, and verify recovery |
| 06 | [Production Patterns & Deliverables](./06-bonus-lecture.md) | Learn burn-rate alerting, escalation, governance, and submit evidence |

Start with **01-alertmanager-fundamentals.md**.
