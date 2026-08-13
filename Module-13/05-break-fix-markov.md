# 05 — Break/Fix: Markov Prediction Drill

This is the capstone exercise for Module 13. You will inject load to push a system into the "Degraded" state, watch the Markov model calculate a rising probability of failure, and observe the automated playbook trigger to restore the system to "Healthy" before it actually fails.

---

## The Scenario

A web application is running normally in the Healthy state. A traffic spike begins pushing CPU and memory into the Degraded range. Your Markov model monitors the state transitions in real time. As the system degrades further toward Critical, the forecast calculates an increasing probability of failure. When the probability exceeds 60%, a webhook fires to trigger an Ansible remediation playbook that scales up the infrastructure before any actual failure occurs.

---

## Step 1: Start the Lab Environment

```bash
cd Module-13/lab
docker compose up -d --build
```

Verify the service is running:

```bash
curl -s http://localhost:5002/health | python3 -m json.tool
```

```json
{
  "status": "healthy",
  "current_state": "Healthy",
  "uptime_seconds": 12
}
```

Check the initial state:

```bash
curl -s http://localhost:5002/api/state | python3 -m json.tool
```

```json
{
  "state": "Healthy",
  "cpu": 28.3,
  "mem": 42.1,
  "disk": 35.0,
  "error_rate": 0.02,
  "timestamp": "2026-08-06T14:00:00Z"
}
```

---

## Step 2: Load the Transition Matrix

Ensure you have a transition matrix from Lesson 03:

```bash
ls -la data/transition_matrix.csv
```

If not, generate it:

```bash
python3 scripts/generate_state_data.py
python3 scripts/build_transition_matrix.py
```

---

## Step 3: Run the Baseline Forecast

Before injecting load, forecast from the current Healthy state:

```bash
python3 scripts/forecast.py --state Healthy --matrix data/transition_matrix.csv --steps 6
```

```text
═══════════════════════════════════════════════════════════════
  Markov Chain Failure Forecast
═══════════════════════════════════════════════════════════════
  Current state:     Healthy
  Forecast horizon:  6 steps (30 minutes)

  Step-by-Step Forecast:
    Step 1:  P(Failed) =  0.4%
    Step 2:  P(Failed) =  1.2%
    Step 3:  P(Failed) =  2.1%
    Step 4:  P(Failed) =  2.8%
    Step 5:  P(Failed) =  3.1%
    Step 6:  P(Failed) =  3.2%

  ✅ Below threshold (60%). No remediation needed.
═══════════════════════════════════════════════════════════════
```

Good. From Healthy, failure probability is negligible.

---

## Step 4: Inject Load

Push the system into the Degraded state:

```bash
curl -X POST http://localhost:5002/drill/inject-load
```

```json
{
  "drill": "inject-load",
  "active": true,
  "phase": "degradation",
  "note": "System will transition Healthy → Degraded → Critical over 5 minutes (accelerated)"
}
```

The drill uses an accelerated clock: every 10 seconds, the system advances one simulated time step. The load injection pushes metrics up gradually.

---

## Step 5: Collect Live State Data

Start collecting state snapshots from the running app:

```bash
python3 scripts/collect_live.py --duration 300 --output data/live_states.csv
```

In a separate terminal, watch the state transitions:

```bash
watch -n 5 'curl -s http://localhost:5002/api/state | python3 -m json.tool'
```

You should see the state progress:

```text
t=0s:   { "state": "Healthy",  "cpu": 28.3, ... }
t=30s:  { "state": "Healthy",  "cpu": 45.1, ... }
t=60s:  { "state": "Degraded", "cpu": 67.2, ... }  ← transition!
t=90s:  { "state": "Degraded", "cpu": 72.8, ... }
t=120s: { "state": "Critical", "cpu": 84.1, ... }  ← transition!
t=150s: { "state": "Critical", "cpu": 88.5, ... }
```

---

## Step 6: Watch the Forecast Rise

As the system enters Critical, run the forecast again:

```bash
python3 scripts/forecast.py --state Critical --matrix data/transition_matrix.csv --steps 6
```

```text
  Final P(Failed) at step 6: 55.0%
  ✅ Below threshold (60%). Close — monitoring.
```

Increase the horizon:

```bash
python3 scripts/forecast.py --state Critical --matrix data/transition_matrix.csv --steps 10
```

```text
  Final P(Failed) at step 10: 59.1%
  ✅ Below threshold (60%). Very close.
```

One more step:

```bash
python3 scripts/forecast.py --state Critical --matrix data/transition_matrix.csv --steps 13
```

```text
  Final P(Failed) at step 13: 60.1%
  ⚠️ THRESHOLD EXCEEDED — Triggering remediation webhook!
  📡 POST http://localhost:5001/ansible-trigger
  ✅ Webhook delivered successfully
```

---

## Step 7: Observe the Automated Remediation

Check the Docker logs to see the Markov app receive the remediation signal:

```bash
docker compose logs -f app
```

```text
[MARKOV] State transition: Healthy → Degraded (cpu=67.2%)
[MARKOV] State transition: Degraded → Critical (cpu=84.1%)
[MARKOV] ⚠️ Forecast: P(Failed) = 60.1% at step 13 — THRESHOLD EXCEEDED
[MARKOV] 📡 Webhook sent to http://localhost:5001/ansible-trigger
[MARKOV] 🔧 Remediation received — executing scale-up
[MARKOV] State transition: Critical → Degraded (load reduced)
[MARKOV] State transition: Degraded → Healthy (system recovered)
[MARKOV] ✅ System restored to Healthy state
```

Key observation: **the system never reached the Failed state**. The Markov model predicted failure and triggered remediation while the system was still Critical.

---

## Step 8: Verify Recovery

```bash
curl -s http://localhost:5002/api/state | python3 -m json.tool
```

```json
{
  "state": "Healthy",
  "cpu": 32.1,
  "mem": 44.5,
  "disk": 35.0,
  "error_rate": 0.03,
  "timestamp": "2026-08-06T14:08:00Z"
}
```

Run a post-recovery forecast:

```bash
python3 scripts/forecast.py --state Healthy --matrix data/transition_matrix.csv --steps 6
```

```text
  Final P(Failed) at step 6: 3.2%
  ✅ Below threshold (60%). System is stable.
```

---

## Step 9: Reset and Review

```bash
curl -X POST http://localhost:5002/drill/reset
```

Check the drill timeline via the API:

```bash
curl -s http://localhost:5002/api/drill-log | python3 -m json.tool
```

```json
{
  "events": [
    {"time": "14:00:00Z", "event": "drill_started", "state": "Healthy"},
    {"time": "14:01:00Z", "event": "state_change", "from": "Healthy", "to": "Degraded"},
    {"time": "14:02:00Z", "event": "state_change", "from": "Degraded", "to": "Critical"},
    {"time": "14:03:30Z", "event": "forecast_alert", "p_failed": 0.601, "steps": 13},
    {"time": "14:03:30Z", "event": "webhook_sent", "target": "ansible-trigger"},
    {"time": "14:04:00Z", "event": "remediation_applied", "action": "scale-up"},
    {"time": "14:05:00Z", "event": "state_change", "from": "Critical", "to": "Degraded"},
    {"time": "14:06:00Z", "event": "state_change", "from": "Degraded", "to": "Healthy"},
    {"time": "14:06:00Z", "event": "drill_completed", "outcome": "prevented"}
  ]
}
```

---

## Step 10: Write the Report

```markdown
## Markov Predictive Remediation Report

**Drill type:** Load injection → state degradation
**Start state:** Healthy
**Peak state:** Critical (never reached Failed)
**Forecast trigger:** P(Failed) = 60.1% at step 13 (65 minutes horizon)
**Remediation action:** scale-up via Ansible webhook
**Time to detect degradation:** 60 seconds
**Time to predict failure:** 90 seconds after Critical
**Time to remediate:** 120 seconds after webhook
**Outcome:** System restored to Healthy — failure prevented

**Key takeaway:** The Markov model predicted failure 65 simulated
minutes in advance. Combined with Module 10 auto-remediation, the
system recovered without any user impact or actual failure.
```

---

## Connecting Modules 9–13

| Module | Prediction Method | What It Predicts | Best For |
|---|---|---|---|
| Module 9 | Linear regression | When a metric hits a limit | Steady growth (disk, user count) |
| Module 13 | Markov chains | What state the system will be in | Cascading failures, state transitions |

Together, they cover both prediction patterns:
- Module 9 catches **slow burns** (disk filling over weeks).
- Module 13 catches **fast cascades** (healthy → degraded → critical in minutes).

---

## Completion Criteria

- [ ] Lab environment started with `docker compose up`.
- [ ] Baseline forecast run from Healthy state (low failure probability).
- [ ] Load injected via drill endpoint.
- [ ] State transitions observed: Healthy → Degraded → Critical.
- [ ] Forecast run from Critical state showing rising P(Failed).
- [ ] Threshold exceeded — webhook triggered automatically.
- [ ] System recovered to Healthy without reaching Failed.
- [ ] Drill log reviewed and report written.
- [ ] Lab reset and environment cleaned up.
