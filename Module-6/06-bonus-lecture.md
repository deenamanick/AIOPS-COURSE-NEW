# 06 — OpenTelemetry, Tracing & Deliverables

Prometheus and Loki provide two pillars of observability. Distributed tracing completes the lab's conceptual model by showing how one request moves through several services and where it spends time.

---

## OpenTelemetry

OpenTelemetry (OTel) is a vendor-neutral set of APIs, SDKs, semantic conventions, and collectors for producing and transporting telemetry. It is not a storage or visualization backend by itself.

```text
Instrumented services
   metrics ─┐
   logs ────┼──► OpenTelemetry Collector ──► Prometheus / Loki / Jaeger
   traces ──┘          receive, process, export
```

The Collector separates instrumentation from backend choice. A common pipeline has:

- **Receivers** accepting OTLP, Prometheus, or other input.
- **Processors** batching, sampling, filtering, or redacting telemetry.
- **Exporters** sending data to one or more backends.

---

## Trace Anatomy

A **trace** represents an end-to-end operation. A **span** represents one timed unit of work and contains a trace ID, span ID, parent span ID, timestamps, status, and attributes.

```text
Trace: checkout request (840 ms)
├── API gateway span (840 ms)
├── inventory span (75 ms)
├── payment span (610 ms)   ◄── bottleneck
│   └── bank API span (570 ms)
└── notification span (40 ms)
```

Metrics show that p95 latency increased. Logs may contain a payment timeout. A trace identifies the exact dependency and span consuming the time.

### Context Propagation

Services must propagate trace context in request headers. Without it, spans become disconnected traces. Adding a trace ID to structured logs enables a Grafana workflow from metric exemplar → trace → related logs.

---

## Sampling and Cost

Capturing every production trace can be expensive.

| Strategy | Behavior | Tradeoff |
|---|---|---|
| Head sampling | Decide when the request starts | Cheap, but may discard later errors |
| Tail sampling | Decide after the trace completes | Retains errors/slow traces, needs buffering |
| Probabilistic | Keep a percentage | Predictable volume, may miss rare events |
| Rules-based | Keep errors and high latency | High diagnostic value, more configuration |

Telemetry also requires security controls. Redact secrets, tokens, passwords, and personal data before export. Restrict dashboard access and define retention periods.

---

## Production Observability Checklist

- Instrument service boundaries with consistent semantic attributes.
- Use RED for request-driven services and USE for infrastructure.
- Put Golden Signals at the top of operational dashboards.
- Attach service, environment, version, and region consistently.
- Control metric and log label cardinality.
- Define retention, sampling, and cost budgets.
- Connect dashboards to runbooks and alerts to user impact.
- Test telemetry during failure drills; an untested dashboard is only a hypothesis.

---

## Student Deliverables

### Deliverable 1: Prometheus Evidence

Submit:

- Screenshot of the Targets page with Node Exporter and Flask `UP`.
- The CPU, memory, HTTP request-rate, and error-rate PromQL queries.
- A short explanation of pull-based collection and the `up` metric.

### Deliverable 2: Grafana Dashboard

Submit a screenshot or exported dashboard containing:

- CPU gauge.
- Memory time series.
- HTTP request-rate time series.
- HTTP error-rate time series.
- Working target-server variable.

### Deliverable 3: Loki Queries

Submit three LogQL queries:

- Filter by severity or error text.
- Find Nginx 5xx responses.
- Calculate an error count or rate over time.

### Deliverable 4: Incident Correlation Report

Include:

1. Incident timeline.
2. Screenshot of the metric spike.
3. Matching Flask and Nginx log evidence.
4. Root cause and recovery action.
5. One recommended alert or prevention control.

### Deliverable 5: Concept Check

Explain in your own words:

- Monitoring versus observability.
- When to use metrics, logs, and traces.
- RED, USE, and Golden Signals.
- How OpenTelemetry avoids backend lock-in.

---

## Module Summary

You can now collect infrastructure and application metrics, query time series with PromQL, design a Grafana dashboard, aggregate logs with Loki and Promtail, and correlate metric changes with log evidence. You also understand how traces and OpenTelemetry extend this workflow across distributed systems.

In Module 7, you will turn these signals into actionable alerts and use SLIs, SLOs, and error budgets to decide when reliability work takes priority.
