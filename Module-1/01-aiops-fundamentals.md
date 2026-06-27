# 01 — AIOps Fundamentals

## What is AIOps?

**AIOps** (Artificial Intelligence for IT Operations) applies machine learning and data science to automate and enhance IT operations workflows — incident detection, root cause analysis, capacity planning, and auto-remediation.

> Gartner coined the term in 2017: "AIOps platforms utilize big data, modern ML, and other advanced analytics technologies to directly and indirectly enhance IT operations."

In plain terms: **AIOps = AI helping SRE/DevOps teams work faster and smarter.**

---

## AIOps Lifecycle

```
Collect → Observe → Detect → Correlate → Predict → Automate → Remediate
   │         │         │         │           │          │          │
   │         │         │         │           │          │          └─ Self-heal (Ansible, scripts)
   │         │         │         │           │          └─ Trigger actions (webhooks, pipelines)
   │         │         │         │           └─ Forecast failures (ML models, time-series)
   │         │         │         └─ Group related alerts → single incident
   │         │         └─ Anomaly detection (Isolation Forest, Z-score)
   │         └─ Dashboards, alerting (Prometheus, Grafana)
   └─ Metrics, logs, traces, events (Node Exporter, Loki, Jaeger)
```

Each module in this course maps to one or more stages of this lifecycle.

---

## Monitoring vs Observability vs AIOps

| Aspect | Monitoring | Observability | AIOps |
|---|---|---|---|
| **Goal** | "Is it up?" | "Why is it broken?" | "Fix it before users notice" |
| **Approach** | Static thresholds | Rich telemetry + query | ML + automation |
| **Data** | Metrics (CPU, memory) | Metrics + Logs + Traces | All data + correlation |
| **Alert style** | CPU > 90% → page | Explore dashboards, drill down | Anomaly detected → auto-RCA |
| **Human effort** | High (manual RCA) | Medium (guided investigation) | Low (automated detection + suggestion) |
| **Example tool** | Nagios, Zabbix | Prometheus + Grafana + Loki | BigPanda, Moogsoft, or custom ML |

**Key insight**: AIOps doesn't replace monitoring — it builds on top of observability.

---

## SRE and AIOps

Site Reliability Engineering (SRE), as defined by Google, treats operations as a software problem. AIOps amplifies SRE by automating the repetitive parts:

| SRE Practice | AIOps Enhancement |
|---|---|
| Incident response | Auto-correlate alerts, suggest root cause |
| Post-mortem analysis | LLM-generated incident reports |
| Capacity planning | ML-based forecasting (disk full in 14 days) |
| Toil reduction | Auto-remediation playbooks |
| Error budgets | Predictive SLO breach warnings |

---

## The 4 Data Types

| Type | What it is | Example | Tool |
|---|---|---|---|
| **Metrics** | Numeric time-series | CPU = 87% at 14:01:00 | Prometheus, Node Exporter |
| **Logs** | Timestamped text events | `[ERROR] Connection refused to db:3306` | Loki, ELK |
| **Traces** | Request path across services | User → API → Auth → DB (total: 450ms) | Jaeger, OpenTelemetry |
| **Events** | State changes | Deployment v2.3 at 14:00 | K8s events, webhooks |

AIOps ingests all 4 types and correlates them to find patterns humans would miss.

---

## Problems AIOps Solves

| Problem | Impact | AIOps Solution |
|---|---|---|
| **Alert fatigue** | 500 alerts/day, 90% noise | Correlation engine → 500 alerts become 5 incidents |
| **Slow RCA** | MTTR = 2 hours of manual investigation | RAG + LLM → root cause suggested in seconds |
| **Repeated incidents** | Same failure happens monthly | Pattern detection + preventive automation |
| **Capacity blindness** | Disk fills at 3 AM on Saturday | Predictive forecasting → alert 2 days before |
| **Knowledge silos** | Only senior SRE knows the fix | RAG retrieves past incident resolutions |

---

## What You'll Build in This Module

1. **Multi-VM lab** — 2 VMs simulating a real infrastructure (Vagrant + VirtualBox)
2. **Sample application** — Flask + Nginx on app-server
3. **Monitoring foundation** — Node Exporter on every VM
4. **RAG Incident Assistant** — AI-powered incident search using past data
5. **Break/Fix exercises** — Practice troubleshooting real failures

---

## Key Takeaways

- AIOps is the application of AI/ML to IT operations — not a product, but a practice
- It builds on observability (metrics + logs + traces), adding correlation, prediction, and automation
- SRE and AIOps are complementary — SRE defines the goals, AIOps accelerates achieving them
- The course follows the AIOps lifecycle: each module covers one stage from collection through remediation
