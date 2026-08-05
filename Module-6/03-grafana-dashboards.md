# 03 — Grafana Dashboards

Grafana does not collect metrics. It queries data sources such as Prometheus and Loki, then turns the results into panels. A useful dashboard should answer a health question, preserve units, and make abnormal behavior obvious.

---

## Lab 1: Open Grafana and Verify Prometheus

The lab provisions Prometheus automatically as a data source.

1. Open `http://localhost:3000`.
2. Sign in with `admin` / `admin` and change the password if prompted.
3. Go to **Connections → Data sources → Prometheus**.
4. Select **Save & test**.

If creating it manually, use `http://prometheus:9090` from inside Docker—not `localhost`, which would refer to the Grafana container itself.

---

## Lab 2: Create a Target Variable

Create a dashboard, then select **Dashboard settings → Variables → New**.

| Field | Value |
|---|---|
| Name | `instance` |
| Type | Query |
| Data source | Prometheus |
| Query | `label_values(up, instance)` |
| Multi-value | Enabled |
| Include All | Enabled |

Use `instance=~"$instance"` in panel queries. The regex matcher supports one, many, or all selected targets.

---

## Lab 3: Build the Four Required Panels

### Panel 1 — CPU Gauge

```promql
100 * (1 - avg by (instance) (
  rate(node_cpu_seconds_total{mode="idle",instance=~"$instance"}[5m])
))
```

- Visualization: **Gauge**
- Unit: **Percent (0–100)**
- Thresholds: green 0, yellow 70, red 85
- Reduce: Last not null

### Panel 2 — Memory Time Series

```promql
100 * (
  1 - node_memory_MemAvailable_bytes{instance=~"$instance"}
    / node_memory_MemTotal_bytes{instance=~"$instance"}
)
```

- Visualization: **Time series**
- Unit: **Percent (0–100)**
- Legend: `{{instance}}`
- Soft maximum: 100

### Panel 3 — HTTP Request Rate

```promql
sum by (instance) (
  rate(http_requests_total{instance=~"$instance"}[5m])
)
```

- Visualization: **Time series**
- Unit: **requests/sec**
- Legend: `{{instance}}`

### Panel 4 — HTTP Error Rate

```promql
100 * sum by (instance) (
  rate(http_requests_total{status=~"5..",instance=~"$instance"}[5m])
)
/ clamp_min(
  sum by (instance) (rate(http_requests_total{instance=~"$instance"}[5m])),
  0.001
)
```

- Visualization: **Time series**
- Unit: **Percent (0–100)**
- Threshold: red above 5%

Generate mixed traffic:

```bash
for i in $(seq 1 50); do curl -s http://localhost:8080/ > /dev/null; done
for i in $(seq 1 10); do curl -s http://localhost:8080/error > /dev/null; done
```

---

## Dashboard Design Rules

1. Put Golden Signals and user impact at the top; infrastructure details come later.
2. Use consistent units and thresholds. A graph without units is ambiguous.
3. Prefer rates to raw counter totals.
4. Use the same time range across related panels to make correlation possible.
5. Avoid high-cardinality labels such as user IDs, full URLs, or request IDs in metrics.
6. Add a short panel description that states the query's intent.

| Panel type | Best use |
|---|---|
| Stat | One current number, such as availability |
| Gauge | Current value relative to limits |
| Time series | Trends, spikes, and correlation |
| Table | Ranked or multi-field results |
| Heatmap | Latency distributions and histograms |
| Logs | Event context around a metric change |

---

## Validation Checklist

- [ ] Four panels are visible and have correct units.
- [ ] The target variable filters every panel.
- [ ] Normal traffic changes request rate.
- [ ] Error traffic produces an error-rate spike.
- [ ] Dashboard time range and refresh interval are appropriate.

Save the dashboard as **AIOps Service Overview**. In the next lesson, you will add logs to explain the metric spikes.
