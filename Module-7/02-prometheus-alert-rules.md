# 02 — Prometheus Alert Rules

Prometheus alert rules are version-controlled PromQL expressions with labels and annotations. The included lab loads `prometheus/rules/alerts.yml` and sends firing alerts to Alertmanager.

---

## The Three Required Rules

### HighCPU

```promql
100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))) > 80
```

- Required duration: `5m`
- Severity: warning
- Purpose: infrastructure diagnostic signal

### HighErrorRate

```promql
100 * sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
/ clamp_min(sum by (job) (rate(http_requests_total[5m])), 0.001) > 5
```

- Required duration: `2m`
- Severity: critical
- Purpose: page on user-visible failures

### DiskAlmostFull

```promql
100 * (1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}
/ node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}) > 85
```

- Required duration: `5m`
- Severity: warning
- Purpose: act before writes fail

---

## Validate Before Reloading

```bash
docker compose exec prometheus \
  promtool check config /etc/prometheus/prometheus.yml

docker compose exec prometheus \
  promtool check rules /etc/prometheus/rules/alerts.yml
```

Open `http://localhost:9090/rules` and verify that all rules loaded. Use `http://localhost:9090/alerts` to observe inactive, pending, and firing states.

---

## Test HighErrorRate

Generate sustained mixed traffic for longer than the rule's two-minute `for` duration:

```bash
end=$((SECONDS+180))
while [ $SECONDS -lt $end ]; do
  curl -s http://localhost:8080/ > /dev/null
  curl -s http://localhost:8080/error > /dev/null
done
```

Expected sequence:

1. Error-rate expression crosses 5%.
2. `HighErrorRate` becomes pending.
3. After two uninterrupted minutes it becomes firing.
4. Alertmanager groups and routes the alert.
5. Mailpit and the webhook receiver display a notification.

### Safely Test CPU and Disk Logic

Do not fill the host disk merely to test a rule. Use `promtool test rules` with the included `prometheus/tests/alerts.test.yml`:

```bash
docker compose exec prometheus promtool test rules \
  /etc/prometheus/tests/alerts.test.yml
```

Unit tests supply synthetic time series and verify that alerts fire at expected evaluation times. A passing test proves the logic; a controlled staging drill proves integration.

---

## Receiver Options

The lab routes email to Mailpit and also sends a webhook. For production Slack delivery, store the webhook securely and add a receiver similar to:

```yaml
slack_configs:
  - api_url_file: /run/secrets/slack_webhook
    channel: '#sre-alerts'
    send_resolved: true
```

Never commit a real webhook URL, SMTP password, or API token.

---

## Validation Checklist

- [ ] Configuration and rule checks pass.
- [ ] Three required rules appear in Prometheus.
- [ ] HighErrorRate moves through pending to firing.
- [ ] A firing and resolved notification reaches the local receivers.
- [ ] Synthetic CPU and disk tests pass without harming the host.
