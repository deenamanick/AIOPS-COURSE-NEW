# 05 — Break/Fix Activities

This exercise consumes a shortened **training error budget**, applies a release policy, restores the service, and watches the rolling window recover. Production uses the 30-day SLO; the lab uses five minutes so the complete lifecycle is observable during class.

---

## Establish the Baseline

```bash
cd Module-7/lab
docker compose up -d --build
curl -X POST http://localhost:8080/drill/reset
```

Generate successful requests:

```bash
for i in $(seq 1 200); do curl -s http://localhost:8080/ > /dev/null; done
```

Query:

```promql
slo:availability:ratio_5m
```

```promql
slo:error_budget_remaining:ratio_5m
```

---

## Consume the Budget

Generate sustained failures mixed with a smaller amount of success traffic:

```bash
end=$((SECONDS+150))
while [ $SECONDS -lt $end ]; do
  curl -s http://localhost:8080/error > /dev/null
  curl -s http://localhost:8080/ > /dev/null
done
```

Observe:

- availability falls below 99.5%;
- error-budget remaining becomes zero or negative;
- `ErrorBudgetExhausted` fires;
- the local receivers get a critical notification.

Record the start time, request counts, SLI, budget remaining, and alert transition times.

---

## Apply the Policy

When the budget is exhausted:

1. Mark nonessential feature deployment as frozen.
2. Assign an incident owner.
3. Stop failure generation.
4. Confirm the `/health` and `/` routes return 200.
5. Continue safe traffic so the short rolling window replaces bad events with good events.

```bash
end=$((SECONDS+360))
while [ $SECONDS -lt $end ]; do
  curl -s http://localhost:8080/ > /dev/null
  sleep 0.1
done
```

Watch the five-minute training SLI recover. A production 30-day rolling window recovers gradually as failures age out; restarting Prometheus is not recovery and must never be used to erase reliability history.

---

## Break/Fix: Misrouted Critical Alert

Temporarily change the critical child route receiver in `alertmanager/alertmanager.yml` to a nonexistent receiver name. Validate:

```bash
docker compose exec alertmanager amtool check-config \
  /etc/alertmanager/alertmanager.yml
```

The check should fail. Restore the correct receiver, validate again, and reload:

```bash
docker compose restart alertmanager
```

This demonstrates why alert configuration needs CI validation: a monitoring system that cannot notify is itself an availability risk.

---

## Completion Criteria

- [ ] Training availability began near 100%.
- [ ] Sustained failures exhausted the budget.
- [ ] ErrorBudgetExhausted fired and was delivered.
- [ ] The release-freeze policy was applied.
- [ ] Healthy traffic restored the short-window SLI.
- [ ] The Alertmanager configuration error was detected before deployment.
