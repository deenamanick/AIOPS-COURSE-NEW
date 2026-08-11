# 04 — Chaos Engineering

Chaos engineering is the practice of intentionally introducing failures into a system to verify that it can tolerate them. Netflix coined this discipline with their Chaos Monkey tool in 2011. The core principle: **if you don't test your failure modes deliberately, the first test is a real outage at 3 AM.**

---

## The Chaos Engineering Mindset

```text
Traditional testing: "Does the system work when everything is fine?"
Chaos engineering: "Does the system still work when something breaks?"
```

A system is **resilient** only if it has been proven to survive specific failure scenarios. You cannot infer resilience from uptime. A system that has never experienced a node failure has also never proven it can handle one.

---

## Netflix Chaos Monkey Principles

1. **Start with a hypothesis.** "If we kill the Flask app container, the load balancer will reroute traffic to the healthy replica within 10 seconds."
2. **Define the blast radius.** Only affect one container. Never run chaos experiments in production without a controlled scope.
3. **Minimize the blast radius.** Start with the smallest experiment that tests your hypothesis.
4. **Plan your abort conditions.** If the system doesn't recover in 5 minutes, stop the experiment and restore manually.
5. **Run in production (eventually).** Staging chaos only proves staging resilience. Production chaos is the real test—but start in staging.

For this lab, all experiments are scoped to the lab Docker network. No production systems are affected.

---

## The Two Metrics That Matter

| Metric | Definition | Target |
|---|---|---|
| **TTD** (Time to Detect) | Time from failure injection to the first alert firing | < 2 minutes |
| **TTR** (Time to Recover) | Time from failure injection to full service restoration | < 5 minutes with auto-remediation |

You will measure both for each experiment.

---

## Experiment 1: Kill a Process

**Hypothesis**: If the Flask app container is killed, the load balancer will route traffic to the second healthy replica within 10 seconds. No user requests will fail after that window.

**Blast radius**: One container in the lab Docker network.

### Step 1: Start Two Replicas

```bash
cd Module-10/lab
docker compose up --scale app=2 -d
```

Verify both are healthy:

```bash
docker compose ps
```

```text
NAME                STATUS
module10-app-1      Up (healthy)
module10-app-2      Up (healthy)
```

### Step 2: Start the Traffic Generator

```bash
python3 scripts/traffic_gen.py --duration 300 --rps 5
```

This sends 5 requests per second for 5 minutes and records every HTTP response code and latency. Leave it running in the background.

### Step 3: Kill Container 1

Record the injection time:

```bash
INJECT_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
docker kill module10-app-1
echo "Injected at $INJECT_TIME"
```

### Step 4: Watch the Metrics

```bash
curl -s http://localhost:5001/chaos/status | python3 -m json.tool
```

```json
{
  "experiment": "process-kill",
  "healthy_replicas": 1,
  "total_replicas": 2,
  "ttd_seconds": 8,
  "status": "degraded-recovering"
}
```

### Step 5: Measure TTD and TTR

After the traffic generator finishes:

```bash
python3 scripts/analyze_chaos.py --log traffic.log --inject-time "$INJECT_TIME"
```

Expected output:

```text
═══════════════════════════════════════════════════════════════
  Chaos Experiment: Process Kill
═══════════════════════════════════════════════════════════════
  Inject time:         2026-08-11T06:30:00Z
  First alert fired:   2026-08-11T06:30:08Z
  TTD:                 8 seconds ✅ (target: < 2 minutes)
  Service recovered:   2026-08-11T06:30:22Z
  TTR:                 22 seconds ✅ (target: < 5 minutes)
  Failed requests:     3 (of 25 in recovery window)
  Error rate at peak:  12% (recovered to 0%)
═══════════════════════════════════════════════════════════════
```

### What to Look For

- Does the load balancer stop sending requests to the dead container immediately?
- Are any in-flight requests lost (HTTP 502 or 503)?
- Does Alertmanager fire `NginxDown` or `ContainerDown` within 2 minutes?
- Does auto-remediation restart container 1 automatically?

---

## Experiment 2: Network Partition

**Hypothesis**: If we block traffic between `app-server` and `db-server` using `iptables`, the application will return a graceful error (503) rather than hanging indefinitely. The circuit breaker will open within 30 seconds.

**Blast radius**: One `iptables` rule on the lab Docker bridge network.

### Step 1: Identify the Container IPs

```bash
APP_IP=$(docker inspect module10-app-1 \
  --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
DB_IP=$(docker inspect module10-db-1 \
  --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
echo "App: $APP_IP  DB: $DB_IP"
```

### Step 2: Block the Traffic

```bash
INJECT_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# Block TCP from app-server to db-server on port 5432 (PostgreSQL)
sudo iptables -I DOCKER-USER -s "$APP_IP" -d "$DB_IP" -p tcp \
  --dport 5432 -j DROP
echo "Network partition active. Injected at $INJECT_TIME"
```

### Step 3: Observe Application Behavior

```bash
curl -s http://localhost:5001/api/status
```

Expected within 30 seconds of the partition:

```json
{
  "status": "degraded",
  "db_connection": "circuit-open",
  "message": "Database unreachable. Serving cached data.",
  "cache_age_sec": 45
}
```

The app should not hang — the circuit breaker should time out the database call and return a cached or error response.

### Step 4: Restore Connectivity

```bash
sudo iptables -D DOCKER-USER -s "$APP_IP" -d "$DB_IP" -p tcp \
  --dport 5432 -j DROP
echo "Network partition removed"
```

### Step 5: Measure Recovery

```bash
python3 scripts/analyze_chaos.py --log traffic.log --inject-time "$INJECT_TIME"
```

```text
═══════════════════════════════════════════════════════════════
  Chaos Experiment: Network Partition
═══════════════════════════════════════════════════════════════
  Inject time:         2026-08-11T06:45:00Z
  Circuit opened at:   2026-08-11T06:45:28Z   (28 seconds after inject)
  Partition restored:  2026-08-11T06:50:00Z
  Circuit closed at:   2026-08-11T06:50:35Z   (35 seconds after restore)
  TTD:                 28 seconds ✅
  TTR:                 35 seconds ✅
  503 responses:       0  (circuit returned cached data instead of 503)
  Hanged requests:     0
═══════════════════════════════════════════════════════════════
```

### What to Look For

- Did any requests hang indefinitely (no timeout)?
- Did the circuit breaker open automatically?
- Did the app serve stale/cached data or return a clear error?
- Did the circuit breaker close automatically after connectivity was restored?

---

## Experiment 3: Resource Starvation

**Hypothesis**: If we consume 95% of available CPU using `stress-ng`, the `HighCPULoad` alert will fire within 5 minutes and the auto-scaling playbook will add a replica.

**Blast radius**: CPU on the lab host only. Memory and disk are unaffected.

### Step 1: Start the CPU Stress

```bash
INJECT_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# Consume 95% CPU for 10 minutes using 4 worker processes
stress-ng --cpu 4 --cpu-load 95 --timeout 600s &
STRESS_PID=$!
echo "CPU stress started (PID $STRESS_PID). Injected at $INJECT_TIME"
```

### Step 2: Watch the Simulated CPU Metric

```bash
watch -n 5 "curl -s http://localhost:5001/api/metrics | python3 -m json.tool"
```

The `sim_cpu_usage_pct` metric will rise to reflect the host CPU load.

### Step 3: Wait for the Alert and Auto-Scale

With 5 minutes in high CPU state, `HighCPULoad` should fire and the webhook should trigger `scale-up.yml`.

Watch the remediation log:

```bash
watch -n 2 "curl -s http://localhost:5001/api/remediation-log | python3 -m json.tool | tail -20"
```

### Step 4: Stop the Stress

```bash
kill $STRESS_PID
```

### Step 5: Measure

```bash
python3 scripts/analyze_chaos.py --log traffic.log --inject-time "$INJECT_TIME"
```

```text
═══════════════════════════════════════════════════════════════
  Chaos Experiment: Resource Starvation (CPU)
═══════════════════════════════════════════════════════════════
  Inject time:         2026-08-11T07:00:00Z
  CPU > 80% detected:  2026-08-11T07:00:15Z   (15 seconds)
  HighCPULoad fired:   2026-08-11T07:05:15Z   (5 minutes after threshold)
  Webhook received:    2026-08-11T07:05:16Z
  scale-up.yml done:   2026-08-11T07:05:52Z
  Replicas before:     1
  Replicas after:      2
  TTD:                 5 minutes 15 seconds ✅
  TTR:                 5 minutes 52 seconds ✅
═══════════════════════════════════════════════════════════════
```

---

## Break/Fix Activity: Sequential Chaos

Run all three experiments in sequence and record TTD and TTR for each:

```bash
python3 scripts/run_chaos_sequence.py
```

This script:
1. Runs experiment 1 (process kill) → waits for recovery
2. Runs experiment 2 (network partition) → waits for recovery
3. Runs experiment 3 (resource starvation) → waits for recovery
4. Prints a summary table

Expected output:

```text
═══════════════════════════════════════════════════════════════
  Chaos Engineering Results — Module 10
═══════════════════════════════════════════════════════════════
  Experiment              TTD         TTR         Result
  ─────────────────────────────────────────────────────────────
  Process Kill            8s          22s         ✅ PASS
  Network Partition       28s         35s         ✅ PASS
  Resource Starvation     5m15s       5m52s       ✅ PASS
  ─────────────────────────────────────────────────────────────
  Target: TTD < 2min, TTR < 5min (with auto-remediation)
  All targets met: ✅
═══════════════════════════════════════════════════════════════
```

---

## Game Days

A **game day** is a planned chaos experiment run with the team:

1. **Announce in advance** — everyone knows the blast radius and abort criteria.
2. **Designate a chaos lead** — one person injects, others observe and respond.
3. **Record everything** — screenshots, logs, TTD, TTR, decisions made.
4. **Debrief** — what assumptions were wrong? What did auto-remediation miss?

Run one game day per quarter. Every system that has never survived a game day is a system with untested assumptions.

---

## Validation Checklist

- [ ] Experiment 1: Process killed, traffic rerouted, TTD < 2m, TTR < 5m.
- [ ] Experiment 2: Network partitioned, circuit breaker opened, no hangs.
- [ ] Experiment 3: CPU stressed, `HighCPULoad` fired, auto-scaling ran.
- [ ] Sequential chaos sequence completed with all three passing.
- [ ] TTD and TTR recorded for all three experiments.
- [ ] At least one experiment identified a gap in the system's resilience.
