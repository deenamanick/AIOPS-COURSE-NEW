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

## Understanding the Lab Application (`app/app.py`)

The core of this lab is a small **Flask web server** that is pre-wired with Prometheus metrics and structured logging. Before diving into the lessons, here's what the app does and why each piece matters.

### How Logging Works

When the app starts, it configures Python's logging to write to **two places at once**:
1. A **log file** on disk (default: `app.log`) — this is what Promtail will tail and ship to Loki.
2. The **terminal** (stdout) — so you can see logs in real-time via `docker compose logs`.

Every log line is written in a structured format like:
```text
2024-01-15T10:30:00Z INFO method=GET path=/ status=200 duration=0.0012
```
This key=value format makes it easy to search and filter logs later in Loki using LogQL.

### Prometheus Metrics (Built-In)

The app automatically creates two Prometheus metrics:

| Metric Name | Type | What It Tracks |
|---|---|---|
| `http_requests_total` | **Counter** | Total number of HTTP requests, labeled by method, endpoint, and status code. Goes up by 1 on every request. |
| `http_request_duration_seconds` | **Histogram** | How long each request took (in seconds). Allows you to calculate percentiles (p50, p95, p99). |

These metrics are automatically collected on **every request** — the app starts a stopwatch before processing and records the elapsed time after. The `/metrics` endpoint itself is excluded to avoid counting Prometheus scrapes.

### The 5 Endpoints You'll Use

| Endpoint | What It Does | Why It Exists |
|---|---|---|
| `GET /` | Returns `{"status": "ok"}` | Basic health check — confirms the app is running |
| `GET /health` | Returns `{"status": "healthy"}` | Kubernetes-style liveness probe |
| `GET /error` | Logs an ERROR and returns **HTTP 500** | **Your knob to simulate failures** — hit this to generate error metrics and error logs |
| `GET /slow` | Sleeps for 1 second, then responds | **Your knob to simulate latency** — hit this to generate slow response metrics |
| `GET /metrics` | Returns raw Prometheus metrics text | **Prometheus scrapes this endpoint** every 15 seconds to collect all the counters and histograms |

### How It All Connects

```
  You (curl/browser)
       │
       ▼
  ┌─────────────┐     Prometheus scrapes /metrics every 15s
  │  Flask App  │ ◄──────────────────────────────────────── Prometheus
  │  (port 5000)│
  │             │──── writes logs to app.log ──── Promtail ──── Loki
  └─────────────┘
                                                          Grafana reads
                                                          from both ───► 📊 Dashboards
```

**In practice:** You'll hit `/error` and `/slow` with `curl` to generate bad telemetry, then switch to Grafana to see the spikes appear in real-time on your dashboards and trace them back to specific log entries in Loki.

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
