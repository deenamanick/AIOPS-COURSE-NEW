# 05 — Break/Fix Activities

In this lesson, you will act as the on-call engineer. Capture a healthy baseline, inject two failures, diagnose each from evidence, and restore service. Record the exact time of every action so metric and log timelines can be compared.

---

## Before You Begin

```bash
cd Module-6/lab
docker compose up -d --build
docker compose ps
curl -s http://localhost:8080/health
```

Confirm:

- `up{job="node-exporter"}` is `1`.
- The four Grafana panels contain data.
- `{job="nginx"}` and `{job="flask"}` return recent logs.

Create an incident worksheet:

| Field | Observation |
|---|---|
| Failure start time | |
| User-visible symptom | |
| Metric evidence | |
| Log evidence | |
| Root cause | |
| Recovery time | |

---

## Activity 1: Stop Node Exporter

Inject the failure:

```bash
docker compose stop node-exporter
```

After two scrape intervals, query:

```promql
up{job="node-exporter"}
```

Expected behavior:

- `up` changes from `1` to `0`.
- CPU and memory panels develop a gap because no new samples arrive.
- The Flask request panels continue to work.

Diagnosis:

1. Check **Prometheus → Status → Targets** and read the scrape error.
2. Run `docker compose ps node-exporter`.
3. Distinguish **monitoring failure** from **host failure**: the missing exporter does not prove the host is down.

Restore and verify:

```bash
docker compose start node-exporter
```

`up{job="node-exporter"}` should return to `1`; the historical gap remains, correctly documenting the period when data was unavailable.

---

## Activity 2: Generate Flask 500 Errors

Capture the start time, then inject 60 errors:

```bash
for i in $(seq 1 60); do
  curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/error
done
```

Investigate in this order:

1. **Metric:** confirm a spike in the Grafana error-rate panel.
2. **Scope:** check whether request rate and infrastructure metrics changed too.
3. **Logs:** run these queries in Grafana Explore:

   ```logql
   {job="nginx",status=~"5.."}
   ```

   ```logql
   {job="flask"} |= "ERROR"
   ```

4. **Correlate:** align the dashboard and log time ranges. Verify the route and status at the spike timestamp.
5. **Conclude:** `/error` deliberately raises an exception; the Flask error record and Nginx 500 access entry confirm the cause.

Compare with:

```promql
100 * sum(rate(http_requests_total{status=~"5.."}[5m]))
  / clamp_min(sum(rate(http_requests_total[5m])), 0.001)
```

---

## Activity 3: Repair a Scrape Configuration

Change the Flask target in `prometheus/prometheus.yml` from `app:5000` to the incorrect `app:5999`, then reload Prometheus:

```bash
docker compose restart prometheus
```

Use `up`, the Targets page, and container logs to identify the bad port. Restore `app:5000`, restart Prometheus, and verify recovery.

This activity demonstrates why configuration changes should be validated before deployment:

```bash
docker compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
```

---

## Debrief Questions

1. Why did stopping Node Exporter create gaps instead of zero CPU values?
2. Which signal detected the 500 incident first: traffic, errors, latency, or saturation?
3. What did logs reveal that the error-rate metric could not?
4. Why is matching timestamps necessary but insufficient to prove causation?
5. Which alert would you create for exporter failure, and how would you avoid noisy transient alerts?

Suggested alert condition:

```promql
up{job="node-exporter"} == 0
```

Require the condition to persist for several minutes in a production alert rule so a single missed scrape does not page the on-call engineer.

---

## Completion Criteria

- [ ] You observed and explained a scrape gap.
- [ ] You restored Node Exporter and verified `up == 1`.
- [ ] You generated a measurable 500-error spike.
- [ ] You correlated the spike with both Flask and Nginx logs.
- [ ] You completed the incident worksheet with evidence-based root cause.
