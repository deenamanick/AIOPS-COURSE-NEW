# 01 — Monitoring vs Observability

Before installing any tools, you need to understand the conceptual difference between **monitoring** and **observability**. These terms are often used interchangeably, but they represent fundamentally different approaches to understanding system health.

---

## Monitoring: Asking Known Questions

Monitoring is the practice of collecting predefined metrics and setting alerts against known thresholds. It answers questions you **already know to ask**:

- "Is CPU above 90%?"
- "Is the API returning 500 errors?"
- "Is disk usage above 80%?"

Monitoring is **reactive**: you decide what to watch in advance, and the system tells you when those specific conditions occur.

---

## Observability: Asking Unknown Questions

Observability is the ability to understand the **internal state** of a system by examining its **external outputs** — without having to predict in advance what might go wrong. It answers questions you **didn't know you needed to ask**:

- "Why did latency spike at 3:14 AM for users in Singapore but not in London?"
- "What changed between the deployment at 2 PM and the error spike at 2:07 PM?"
- "Which specific database query is causing the memory leak?"

Observability is **proactive**: it gives you the tools to explore and diagnose novel, unexpected failures.

| Aspect | Monitoring | Observability |
|---|---|---|
| **Question Type** | Known ("Is X broken?") | Unknown ("Why is X broken?") |
| **Data Sources** | Metrics and alerts | Metrics + Logs + Traces |
| **Approach** | Dashboards + thresholds | Exploration + correlation |
| **Best For** | Known failure modes | Novel, complex, distributed failures |

---

## The 3 Pillars of Observability

Production observability rests on three complementary data types:

```
                        ┌─────────────────────────┐
                        │     OBSERVABILITY       │
                        └────────────┬────────────┘
                 ┌───────────────────┼───────────────────┐
                 ▼                   ▼                   ▼
        ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
        │    METRICS     │  │     LOGS       │  │    TRACES      │
        │                │  │                │  │                │
        │  "What is      │  │  "What         │  │  "What path    │
        │   happening?"  │  │   happened?"   │  │   did it take?"│
        │                │  │                │  │                │
        │  Prometheus    │  │  Loki          │  │  Jaeger /      │
        │  Datadog       │  │  ELK Stack     │  │  OpenTelemetry │
        │  CloudWatch    │  │  Splunk        │  │  Zipkin        │
        └────────────────┘  └────────────────┘  └────────────────┘
```

### Pillar 1: Metrics
**What is happening right now?**
- Numerical time-series data: CPU%, memory%, request rate, error rate, latency percentiles.
- Collected at regular intervals (e.g., every 15 seconds).
- Efficient to store and query (just numbers + timestamps).
- **Tool in this module:** Prometheus

### Pillar 2: Logs
**What happened?**
- Timestamped text records of discrete events: "User login failed", "Database connection timeout", "Pod OOMKilled".
- Rich context: stack traces, request IDs, user identifiers.
- Expensive to store (text is large) but invaluable for debugging.
- **Tool in this module:** Loki + Promtail

### Pillar 3: Traces
**What path did the request take?**
- A trace follows a single request as it flows through multiple microservices.
- Each service adds a "span" (start time, duration, metadata) to the trace.
- Essential for debugging latency in distributed systems ("Which service is slow?").
- **Tool introduced in bonus lecture:** OpenTelemetry / Jaeger

---

## Observability Frameworks

SRE teams use structured frameworks to decide **which metrics matter**. Here are the three most widely adopted:

### The RED Method (for Services)

Developed by Tom Wilkie (Grafana Labs). Use RED for any **request-driven service** (APIs, web servers).

| Signal | What It Measures | PromQL Example |
|---|---|---|
| **R**ate | Requests per second | `rate(http_requests_total[5m])` |
| **E**rrors | Failed requests per second | `rate(http_requests_total{status=~"5.."}[5m])` |
| **D**uration | Request latency (p50, p95, p99) | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` |

### The USE Method (for Infrastructure)

Developed by Brendan Gregg (Netflix). Use USE for any **infrastructure resource** (CPU, memory, disk, network).

| Signal | What It Measures | Example |
|---|---|---|
| **U**tilization | % of resource capacity being used | CPU at 85% utilization |
| **S**aturation | Amount of queued/waiting work | 12 processes in the CPU run queue |
| **E**rrors | Error events on the resource | 3 disk I/O errors in the last minute |

### The Golden Signals (Google SRE)

From the Google SRE book. A superset of RED, applicable to all services.

| Signal | What It Measures |
|---|---|
| **Latency** | Time to serve a request (distinguish between successful and failed requests) |
| **Traffic** | Demand on the system (requests/sec, sessions, transactions) |
| **Errors** | Rate of failed requests (explicit 5xx, implicit timeouts) |
| **Saturation** | How "full" the service is (CPU queue depth, memory pressure, thread pool exhaustion) |

---

## Which Framework Should You Use?

| Scenario | Framework |
|---|---|
| Monitoring an API gateway or web service | **RED** (Rate, Errors, Duration) |
| Monitoring a VM, node, or hardware resource | **USE** (Utilization, Saturation, Errors) |
| Building a comprehensive SRE dashboard | **Golden Signals** (covers both services and infrastructure) |

---

## What's Next

Now that you understand the conceptual foundations, let's install the first pillar. In the next lesson, you will deploy **Prometheus** and **Node Exporter** to your Kubernetes cluster and write your first **PromQL** queries to analyze real system metrics.
