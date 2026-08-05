# 02 — Prometheus & PromQL

Prometheus stores numeric observations as time series. Each series has a metric name, labels, timestamps, and values. In this lab, Prometheus pulls host metrics from Node Exporter and application metrics from a Flask `/metrics` endpoint.

---

## How Prometheus Works

```text
Node Exporter :9100 ─┐
                     ├── scraped every 15s ──► Prometheus :9090
Flask /metrics :5000 ┘                              │
                                                   └──► PromQL
```

Prometheus is primarily **pull based**: the server contacts each configured target. This makes target health visible through the built-in `up` metric. Labels such as `job`, `instance`, `method`, and `status` let one metric represent many dimensions.

| Metric type | Use | Example |
|---|---|---|
| Counter | A value that only increases or resets | `http_requests_total` |
| Gauge | A value that rises and falls | `process_resident_memory_bytes` |
| Histogram | Observations grouped into buckets | `http_request_duration_seconds_bucket` |
| Summary | Client-calculated quantiles and totals | Request duration summary |

Never apply `rate()` to a gauge. Use `rate()` or `increase()` on counters so counter resets are handled correctly.

---

## Lab 1: Start the Stack

From this module directory:

```bash
cd Module-6/lab
docker compose up -d --build
docker compose ps
```

Open Prometheus at `http://localhost:9090`. Select **Status → Targets** and confirm that `node-exporter` and `flask-app` are `UP`.

The scrape configuration is in `lab/prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: node-exporter
    static_configs:
      - targets: [node-exporter:9100]

  - job_name: flask-app
    metrics_path: /metrics
    static_configs:
      - targets: [app:5000]
```

Test target health:

```promql
up
```

A value of `1` means the last scrape succeeded; `0` means Prometheus knows the target but cannot scrape it.

---

## Lab 2: Required PromQL Queries

### CPU Usage Percentage

Node Exporter exposes cumulative CPU seconds by mode. Idle time is converted into busy percentage:

```promql
100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))
```

### Memory Usage Percentage

Available memory is more accurate than free memory because it includes reclaimable cache:

```promql
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
```

### HTTP Request Rate

```promql
sum by (instance) (rate(http_requests_total[5m]))
```

Generate traffic, then run the query again:

```bash
for i in $(seq 1 100); do curl -s http://localhost:8080/ > /dev/null; done
```

### Error Rate Percentage

```promql
100 * sum(rate(http_requests_total{status=~"5.."}[5m]))
  / clamp_min(sum(rate(http_requests_total[5m])), 0.001)
```

### P95 Request Duration

```promql
histogram_quantile(
  0.95,
  sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
)
```

---

## PromQL Building Blocks

| Expression | Meaning |
|---|---|
| `{job="flask-app"}` | Exact label match |
| `{status=~"5.."}` | Regex label match |
| `[5m]` | Range vector covering the last five minutes |
| `rate(counter[5m])` | Per-second average change |
| `sum by (instance)(...)` | Aggregate while retaining `instance` |
| `avg_over_time(gauge[15m])` | Average gauge value over time |

Use a rate window at least four times the scrape interval. With a 15-second scrape interval, one minute is the practical minimum; five minutes produces a steadier dashboard.

---

## Validation Checklist

- [ ] All targets appear in Prometheus.
- [ ] `up{job="node-exporter"}` returns `1`.
- [ ] CPU and memory queries return data.
- [ ] Traffic generation changes the request-rate graph.
- [ ] `/error` requests appear in the error-rate query.

Next, you will turn these queries into a reusable Grafana dashboard.
