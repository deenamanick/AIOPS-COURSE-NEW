# 06 — Break/Fix: Cascading Failure & Root Cause Trace

This is the capstone exercise for Module 8. You will inject a realistic cascading failure into the lab stack, observe the cascade propagate through the dependency chain, and use every tool built in this module—log parser, correlation engine, dependency graph, and pub/sub pipeline—to trace the chain back to a single root cause.

---

## The Scenario

A database server's disk fills up. The cascade:

```text
1. Disk full on postgres       → write queries fail
2. Flask app connection pool   → exhausted (waiting for stuck queries)
3. Flask app responses         → 5xx errors spike
4. Nginx access logs           → error rate climbs
5. Users                       → see error pages
```

Five symptoms, one root cause. Your job is to prove it.

---

## Step 1: Establish the Baseline

```bash
cd Module-8/lab
docker compose up -d --build
```

Generate healthy traffic:

```bash
for i in $(seq 1 200); do
  curl -s http://localhost:8080/ > /dev/null
  curl -s http://localhost:8080/api/users > /dev/null
done
```

Verify the correlation engine shows no incidents:

```bash
docker compose logs correlation-engine | tail -5
```

Parse the access logs and confirm a near-zero error rate:

```bash
docker compose exec nginx cat /var/log/nginx/access.log \
  | python3 lab/scripts/log_parser.py \
  | python3 -c "
import json, sys
lines = [json.loads(l) for l in sys.stdin]
errors = sum(1 for l in lines if l['status'] >= 500)
print(f'Baseline: {len(lines)} requests, {errors} errors ({100*errors/max(len(lines),1):.1f}%)')
"
```

---

## Step 2: Inject the Failure

Trigger the disk-full simulation:

```bash
curl -X POST http://localhost:5000/drill/disk-full
```

This activates a cascade inside the lab:

1. The Postgres simulator begins returning errors on all write operations.
2. The Flask app's connection handler times out waiting for the database.
3. Flask returns HTTP 503 to Nginx.
4. Nginx logs the 503s and forwards them to the user.

---

## Step 3: Generate Load During the Failure

```bash
end=$((SECONDS+120))
while [ $SECONDS -lt $end ]; do
  curl -s http://localhost:8080/api/users > /dev/null
  curl -s http://localhost:8080/api/orders > /dev/null
  sleep 0.1
done
```

---

## Step 4: Observe the Correlation Engine

```bash
docker compose logs -f correlation-engine
```

Expected output sequence:

```text
[FILE-LOGGER]  Logged: DISK_PRESSURE
[CORRELATOR]   DISK_PRESSURE → Incident #1 (1 alert)
[NOTIFIER]     🚨 CRITICAL: DISK_PRESSURE — Disk usage > 95% on postgres

[FILE-LOGGER]  Logged: DB_WRITE_FAILURE
[CORRELATOR]   DB_WRITE_FAILURE → Incident #1 (2 alerts)
[NOTIFIER]     🚨 CRITICAL: DB_WRITE_FAILURE — Database write errors > 0

[FILE-LOGGER]  Logged: CONN_POOL_EXHAUSTED
[CORRELATOR]   CONN_POOL_EXHAUSTED → Incident #1 (3 alerts)
[NOTIFIER]     🚨 CRITICAL: CONN_POOL_EXHAUSTED — Connection pool at 100%

[FILE-LOGGER]  Logged: APP_5XX
[CORRELATOR]   APP_5XX → Incident #1 (4 alerts)
[NOTIFIER]     🚨 CRITICAL: APP_5XX — HTTP 5xx error rate > 5%

[FILE-LOGGER]  Logged: USER_IMPACT
[CORRELATOR]   USER_IMPACT → Incident #1 (5 alerts)
[NOTIFIER]     ℹ️  warning: USER_IMPACT — User-facing error rate elevated

[CORRELATOR]   Incident #1 closed — 5 alerts correlated in 120s window
[RCA] Analyzing incident #1...
[RCA]   DISK_PRESSURE       → service: postgres   (depth: 0)
[RCA]   DB_WRITE_FAILURE    → service: postgres   (depth: 0)
[RCA]   CONN_POOL_EXHAUSTED → service: flask-app  (depth: 1)
[RCA]   APP_5XX             → service: flask-app  (depth: 1)
[RCA]   USER_IMPACT         → service: nginx      (depth: 2)
[RCA] ───────────────────────────────────────────────────────
[RCA] ROOT CAUSE:  DISK_PRESSURE (postgres)
[RCA] SYMPTOMS:    DB_WRITE_FAILURE, CONN_POOL_EXHAUSTED, APP_5XX, USER_IMPACT
[RCA] REASONING:   postgres is the deepest alerting dependency
```

---

## Step 5: Analyze the Logs

Parse the Nginx access logs generated during the failure window:

```bash
docker compose exec nginx cat /var/log/nginx/access.log \
  | python3 lab/scripts/log_parser.py \
  | python3 -c "
import json, sys
from collections import defaultdict

lines = [json.loads(l) for l in sys.stdin]
by_minute = defaultdict(lambda: {'total': 0, 'errors': 0})
for l in lines:
    minute = l['timestamp'][:16]  # YYYY-MM-DDTHH:MM
    by_minute[minute]['total'] += 1
    if l['status'] >= 500:
        by_minute[minute]['errors'] += 1

print(f\"{'Minute':<20} {'Total':>6} {'Errors':>7} {'Rate':>7}\")
print('-' * 42)
for minute in sorted(by_minute):
    d = by_minute[minute]
    rate = 100 * d['errors'] / max(d['total'], 1)
    marker = ' ← SPIKE' if rate > 10 else ''
    print(f\"{minute:<20} {d['total']:>6} {d['errors']:>7} {rate:>6.1f}%{marker}\")
"
```

You should see a clear spike in error rate that correlates with the timeline of the injected failure.

---

## Step 6: Remediate

Fix the root cause:

```bash
curl -X POST http://localhost:5000/drill/reset
```

Generate recovery traffic:

```bash
for i in $(seq 1 200); do
  curl -s http://localhost:8080/api/users > /dev/null
done
```

Verify all services return 200 and the error rate drops to zero.

---

## Step 7: Write the Incident Report

Document using this template:

```markdown
## Incident Report — Incident #1

**Root Cause:** Disk full on postgres (simulated)
**Impact:** HTTP 5xx error rate spiked to ~50% for users
**Duration:** ~2 minutes
**Detection:** Correlation engine grouped 5 alerts in 120s window

### Timeline
| Time  | Event |
|-------|-------|
| 14:01 | DISK_PRESSURE alert fired |
| 14:01 | DB_WRITE_FAILURE alert fired |
| 14:02 | CONN_POOL_EXHAUSTED alert fired |
| 14:02 | APP_5XX alert fired |
| 14:03 | USER_IMPACT alert fired |
| 14:03 | Incident #1 created — root cause: postgres |
| 14:05 | Drill reset — disk freed |
| 14:06 | Error rate returned to 0% |

### Cascade Chain
postgres (disk full) → postgres (write failures) → flask-app (pool exhausted)
→ flask-app (5xx) → nginx → users

### Prevention
- Monitor disk usage with predictive alerts (Module 9: Capacity Planning)
- Set disk usage alert at 80% (warning) and 90% (critical)
- Implement automated disk cleanup or volume expansion
```

---

## Completion Criteria

- [ ] Baseline showed near-zero error rate.
- [ ] Disk-full simulation triggered a cascading failure.
- [ ] The correlation engine grouped all alerts into one incident.
- [ ] The RCA module correctly identified `DISK_PRESSURE` on `postgres` as root cause.
- [ ] Log analysis showed a clear error-rate spike correlated with the failure window.
- [ ] Remediation restored the service to healthy state.
- [ ] An incident report was written with timeline, cascade chain, and prevention action.

---

## Module Summary

You can now parse unstructured logs into structured JSON, enrich them with context, correlate multiple alerts into a single incident using time windows, walk a dependency graph to identify root cause versus symptoms, and decouple event producers from consumers using pub/sub. In Module 9, you will use time-series forecasting to predict failures before they cascade.
