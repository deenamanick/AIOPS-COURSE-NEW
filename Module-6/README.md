# Module 6: Observability — Metrics, Logs & Traces

Welcome to Module 6! In Module 5, you built machine learning models to detect anomalies in telemetry data. But where does that telemetry come from? How do you collect CPU metrics from hundreds of servers? How do you search through millions of log lines to find the one error that caused an outage? In this module, you will build a complete **observability stack** using **Prometheus** (metrics), **Grafana** (dashboards), **Loki** (logs), and **Promtail** (log shipping). You will learn the three pillars of observability, master PromQL and LogQL query languages, and practice the real-world SRE workflow of correlating metrics with logs to diagnose production incidents.

---

## Learning Objectives

By the end of this module, you will be able to:
1. Explain the difference between **monitoring** and **observability** and when each is appropriate.
2. Set up **Prometheus** to scrape and store infrastructure and application metrics.
3. Write **PromQL** queries to analyze CPU usage, memory usage, and HTTP request rates.
4. Build **Grafana** dashboards with gauges, time-series panels, and template variables.
5. Aggregate logs using **Loki** and **Promtail** and query them with **LogQL**.
6. Apply the **RED**, **USE**, and **Golden Signals** methodologies to evaluate system health.
7. Correlate metric spikes with log entries to perform root cause analysis.

---

## Prerequisites

- ✅ Module 5 completed (anomaly detection concepts understood)
- ✅ Docker Engine and Docker Compose v2 installed
- ✅ `curl` and a web browser available
- ✅ At least **4GB RAM** available on the host machine (8GB recommended)

---

## Lab Architecture

In this module, you will deploy a full observability stack alongside an instrumented Flask service. The same components can later be moved to Kubernetes with Helm.

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                       DOCKER LAB NETWORK                              │
  │                                                                        │
  │   ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐  │
  │   │  Prometheus  │   │    Loki      │   │        Grafana           │  │
  │   │  (Metrics)   │   │   (Logs)     │   │     (Dashboards)        │  │
  │   │              │   │              │   │                          │  │
  │   │  Scrapes     │   │  Receives    │   │  ┌────────┐ ┌────────┐  │  │
  │   │  every 15s   │   │  log streams │   │  │CPU Gauge│ │Req Rate│  │  │
  │   └──────┬───────┘   └──────┬───────┘   │  ├────────┤ ├────────┤  │  │
  │          │                  │            │  │Mem Time │ │Err Rate│  │  │
  │          │ (pull)           │ (push)     │  │ Series  │ │ Panel  │  │  │
  │          │                  │            │  └────────┘ └────────┘  │  │
  │   ┌──────┴──────────────────┴───────┐   └──────────────────────────┘  │
  │   │                                 │                                  │
  │   │   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐        │
  │   │   │ Node Exporter │  │   Promtail    │  │  AIOps App    │        │
  │   │   │ (system CPU,  │  │ (tails logs,  │  │ (Flask/       │        │
  │   │   │  memory, disk)│  │  ships to     │  │  Streamlit)   │        │
  │   │   │               │  │  Loki)        │  │               │        │
  │   │   └───────────────┘  └───────────────┘  └───────────────┘        │
  │   └─────────────────────────────────────────────────────────────────┘  │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## How to Set Up the Lab

### Step 1: Verify Docker

```bash
docker --version
docker compose version
```

### Step 2: Start the Lab

```bash
cd Module-6/lab
docker compose up -d --build
docker compose ps
```

### Step 3: Open the Tools

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin` / `admin`)
- Flask app through Nginx: `http://localhost:8080`
- Loki readiness endpoint: `http://localhost:3100/ready`

---

## Lessons in this Module

| # | Lesson | What You'll Do |
|---|---|---|
| 01 | [Monitoring vs Observability](./01-monitoring-vs-observability.md) | Understand the 3 Pillars, RED/USE/Golden Signals frameworks |
| 02 | [Prometheus & PromQL](./02-prometheus-promql.md) | Install Prometheus + Node Exporter, write 3 PromQL queries |
| 03 | [Grafana Dashboards](./03-grafana-dashboards.md) | Build a 4-panel dashboard with gauges, time-series, and variables |
| 04 | [Loki Log Aggregation](./04-loki-log-aggregation.md) | Install Loki + Promtail, query logs with LogQL, correlate with metrics |
| 05 | [Break/Fix Activities](./05-break-fix.md) | Stop Node Exporter, generate 500 errors, practice metric-to-log correlation |
| 06 | [Bonus Lecture](./06-bonus-lecture.md) | OpenTelemetry, distributed tracing, production observability patterns, deliverables |

Let's get started with **01-monitoring-vs-observability.md**!
