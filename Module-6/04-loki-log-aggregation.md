# 04 — Loki Log Aggregation & LogQL

Metrics tell you that an incident exists; logs provide the event-level evidence needed to explain it. Loki indexes labels rather than the full text of every log line, while Promtail discovers files, attaches labels, and ships entries to Loki.

> Promtail is used here because it is part of the stated course lab. For new production designs, plan a migration path to an OpenTelemetry-compatible collector or another supported Loki client.

---

## Data Flow

```text
Nginx access.log ─┐
                  ├──► Promtail ──► Loki :3100 ──► Grafana Explore
Flask app.log ────┘       labels       streams          LogQL
```

The included Promtail configuration mounts `lab/logs` and creates two jobs: `nginx` and `flask`. Start or refresh the stack:

```bash
cd Module-6/lab
mkdir -p logs/nginx logs/flask
docker compose up -d --build
docker compose ps
```

Open Grafana and verify the provisioned Loki data source under **Connections → Data sources**.

---

## LogQL Fundamentals

LogQL begins with a label selector, then optionally applies line filters and parsers.

### View All Flask Logs

```logql
{job="flask"}
```

### Search for Error Patterns

```logql
{job="flask"} |= "ERROR"
```

Regex search for several failure terms:

```logql
{job="flask"} |~ "(?i)(error|exception|timeout|failed)"
```

### Filter Nginx 5xx Requests

Promtail parses the combined access-log format and adds a `status` label:

```logql
{job="nginx", status=~"5.."}
```

### Calculate Error Log Rate

```logql
sum(rate({job="flask"} |= "ERROR" [5m]))
```

### Count Errors by Status

```logql
sum by (status) (count_over_time({job="nginx",status=~"5.."}[5m]))
```

---

## Lab: Correlate Metrics and Logs

1. In Grafana, set the dashboard and Explore time range to **Last 15 minutes**.
2. Generate normal requests and note the HTTP request-rate panel.
3. Generate errors:

   ```bash
   for i in $(seq 1 40); do curl -s http://localhost:8080/error > /dev/null; done
   ```

4. Observe the error-rate spike in the Prometheus panel.
5. Drag-select the spike's time interval.
6. Open **Explore → Loki** with the same time range.
7. Run `{job="flask"} |= "ERROR"`, expand one entry, and record its timestamp, route, and status.
8. Compare it with `{job="nginx",status=~"5.."}` to verify that both layers saw the same failure.

This is correlation, not automatically proof of causation. Confirm timestamps, request context, deployments, and dependencies before declaring a root cause.

---

## Labels and Cardinality

Good labels have a small, bounded set of values: `environment`, `service`, `severity`, `status`, and `region`. Do not label logs with request IDs, timestamps, user IDs, or raw URLs; each unique value creates another stream. Keep high-cardinality fields in the log body and filter them after selecting a stream.

| Good label | Poor label |
|---|---|
| `service="api"` | `request_id="4f..."` |
| `severity="error"` | `user_email="..."` |
| `status="500"` | `timestamp="..."` |

---

## Troubleshooting

```bash
docker compose logs promtail
docker compose logs loki
curl -s http://localhost:3100/ready
ls -l logs/nginx logs/flask
```

- No files: generate traffic through Nginx on port `8080`.
- Files exist but no streams: check Promtail mount paths and positions.
- Streams exist but query is empty: widen the Grafana time range and verify labels.
- Duplicate entries: do not delete the positions file while Promtail is running.

Next, you will deliberately break the stack and use metrics-to-logs correlation to diagnose it.
