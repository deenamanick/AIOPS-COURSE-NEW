# 05 — Capstone: Full Incident Lifecycle

This is the capstone exercise for the entire AIOps course. You will execute the complete incident lifecycle end-to-end, using every tool and technique from Modules 1–10, in sequence, against a single injected failure. Nothing is mocked — the disk actually fills, the alert actually fires, the Ansible playbook actually runs, and the LLM actually generates the RCA report.

The capstone IS the break/fix. There are no separate instructions for what to do if something goes wrong — figuring that out using the tools you have built is the exercise.

---

## The Scenario

A database server's write-ahead log (WAL) archive directory begins accumulating files faster than the rotation job clears them. Disk usage grows steadily from 20% toward 100% over approximately 8 simulated hours (8 minutes at the lab's accelerated clock). Your job is to:

1. Detect the trend before it becomes an outage
2. Understand why it is happening using logs and correlation
3. Forecast when it will cause a failure
4. Let the LLM generate the preliminary RCA
5. Remediate with the Ansible playbook
6. Verify the system returns to healthy state
7. Write the blameless post-mortem

---

## Pre-Capstone Checklist

Before you begin, verify all tools are ready:

```bash
# Module 9-style forecast engine
python3 -c "from sklearn.linear_model import LinearRegression; print('sklearn ✅')"

# Module 10 Ansible
ansible --version | head -1

# Module 11 Ollama
curl -s http://localhost:11434/api/tags | python3 -m json.tool | grep name

# Lab app
curl -s http://localhost:5002/health
```

All four must succeed before starting. If Ollama is not running:

```bash
ollama serve &
sleep 2
ollama pull llama3.2:3b
```

---

## Step 1: Establish the Baseline

```bash
cd Module-11/lab
docker compose up -d --build
```

Verify the system is healthy:

```bash
curl -s http://localhost:5002/api/metrics | python3 -m json.tool
```

```json
{
  "disk_usage_pct": 20.0,
  "cpu_usage_pct": 24.8,
  "memory_usage_pct": 41.3,
  "error_rate_pct": 0.4,
  "replicas": 1,
  "timestamp": "2026-08-11T07:00:00Z"
}
```

Record the baseline. Disk should be at or near 20%. Error rate should be below 1%.

---

## Step 2: Inject the Failure

Record the exact inject time:

```bash
INJECT_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "Capstone started at: $INJECT_TIME"

# Inject the disk growth (WAL archive simulation)
curl -X POST http://localhost:5002/drill/wal-growth
```

Expected response:

```json
{
  "drill": "wal-growth",
  "active": true,
  "start_disk_pct": 20.3,
  "growth_rate_pct_per_hour": 9.8,
  "estimated_hours_to_full": 8.1,
  "note": "Accelerated clock: 10 seconds real = 1 simulated hour"
}
```

Do NOT reset the drill during the capstone. Let it run to completion.

---

## Step 3: Detection — Anomaly Detection Fires

Wait approximately 90 seconds (9 simulated hours). The disk metric rises through 40%, then 60%, then 80%.

At approximately 87%:

```bash
watch -n 5 "curl -s http://localhost:5002/api/metrics | python3 -m json.tool"
```

The `DiskAlmostFull` alert will fire in Alertmanager after 2 minutes in the firing state. The Module 5-style anomaly score will exceed 70 (HIGH) as disk crosses 75%.

Check the anomaly score:

```bash
curl -s http://localhost:5002/api/anomaly | python3 -m json.tool
```

```json
{
  "disk_anomaly_score": 82.4,
  "error_rate_anomaly_score": 12.1,
  "latency_anomaly_score": 8.3,
  "composite_score": 43.2,
  "severity": "HIGH",
  "timestamp": "2026-08-11T07:01:30Z"
}
```

Record the first time `disk_anomaly_score > 70` — this is your **TTD (Time to Detect)**.

---

## Step 4: Correlation — Understand the Impact

By the time disk reaches 87%, application errors will have started. Check the logs:

```bash
curl -s http://localhost:5002/api/logs | python3 -m json.tool
```

Look for the cascade pattern:
- WAL archive rotation failure (disk layer)
- Database write errors (DB layer)
- Application connection timeouts (app layer)
- 5xx errors on API endpoints (user-facing layer)

Run the Module 8-style correlation:

```bash
python3 scripts/correlate_alerts.py
```

Expected output:

```text
═══════════════════════════════════════════════════════════════
  Alert Correlation Analysis
═══════════════════════════════════════════════════════════════
  Root alert:    DiskAlmostFull (db-server-01) — fired at 07:01:45Z
  Correlated:    DBConnectionErrors (2m 10s after root alert)
  Correlated:    AppSlowResponse  (2m 35s after root alert)
  Correlated:    HighErrorRate    (3m 05s after root alert)

  Likely cascade: Disk full → WAL write fail → DB timeout → App 5xx
═══════════════════════════════════════════════════════════════
```

---

## Step 5: Prediction — Forecast the Exhaustion

Run the Module 9-style forecasting engine on the live metric:

```bash
python3 scripts/live_forecast.py --metric disk --output output/capstone_forecast.txt
cat output/capstone_forecast.txt
```

Expected output:

```text
═══════════════════════════════════════════════════════════════
  Live Disk Forecast (Capstone)
═══════════════════════════════════════════════════════════════
  Current value:   87.3%
  Growth rate:     +9.8%/hr
  Hours to 100%:   1.3 hours
  Predicted time:  2026-08-11T08:18:00Z
  R² score:        0.96

  🚨 PREDICTIVE ALERT: Disk will exhaust in < 2 hours!
═══════════════════════════════════════════════════════════════
```

---

## Step 6: LLM RCA — Generate the Incident Report

Collect all incident data and generate the RCA:

```bash
# Build the prompt from live data
python3 scripts/build_prompt.py \
  --include-logs \
  --include-alerts \
  --include-anomaly \
  --include-forecast \
  --output prompts/capstone_context.txt

# Generate the RCA with the local LLM
python3 scripts/generate_rca.py \
  --context prompts/capstone_context.txt \
  --model llama3.2:3b \
  --output output/capstone_rca.md

echo "RCA generated: output/capstone_rca.md"
cat output/capstone_rca.md
```

The LLM will generate:
- A one-sentence summary
- A timeline from the WAL error to the current state
- The root cause (WAL archive directory not covered by log rotation)
- The recommended fix (clear-logs.yml playbook, targeting WAL archive dir)
- Three prevention steps

Review the RCA. Verify there are no hallucinated metrics. Check that the root cause matches your manual analysis from Step 4.

---

## Step 7: Remediation — Run the Ansible Playbook

Apply the fix the LLM recommended:

```bash
ansible-playbook \
  -i ../Module-10/lab/playbooks/inventory.ini \
  ../Module-10/lab/playbooks/clear-logs.yml \
  --connection=local \
  -v
```

The playbook will:
1. Find log files older than 7 days (simulated in the lab)
2. Delete them
3. Report disk usage before and after

In parallel, the webhook receiver (running via `docker compose`) will detect the `DiskAlmostFull` alert and also trigger the playbook automatically. You may see the playbook called twice — that is correct behaviour demonstrating the deduplication logic from Module 10.

After the playbook runs, the lab app applies the simulated disk recovery:

```bash
curl -s http://localhost:5002/api/metrics | python3 -m json.tool
```

Disk should drop below 30%. Error rate should recover to baseline.

---

## Step 8: Verify Recovery

Confirm all three layers have recovered:

```bash
# Layer 1: Infrastructure metric
curl -s http://localhost:5002/api/metrics | python3 -m json.tool
# disk_usage_pct should be < 30

# Layer 2: Anomaly scores
curl -s http://localhost:5002/api/anomaly | python3 -m json.tool
# disk_anomaly_score should be < 40 (GREEN)

# Layer 3: Application health
curl -s http://localhost:5002/api/status | python3 -m json.tool
# status should be "healthy"
```

Record the recovery time. Calculate:

```text
TTD = time of first anomaly score > 70 MINUS inject time
TTR = time all three layers healthy MINUS inject time
```

Target: **TTD < 2 minutes, TTR < 10 minutes** (including LLM analysis time).

---

## Step 9: Write the Post-Mortem

Fill in the blameless post-mortem template using all the data you collected:

```bash
cp lab/templates/post-mortem-template.md lab/output/capstone-post-mortem.md
```

Required content:
- **Impact**: Duration, user impact (503 errors on checkout), affected services
- **Timeline**: Use exact timestamps from your notes; minimum 8 events
- **Root Cause**: Apply 5 Whys; the root cause is the log rotation configuration gap
- **What Went Well**: Credit the anomaly detection, the LLM-generated RCA, the Ansible automation
- **What Went Wrong**: What would have prevented detection delay or extended MTTR?
- **Action Items**: At minimum — WAL retention policy, predictive alert for WAL directory, reduce DB connection timeout

---

## Full Capstone Record

After completing all 9 steps, run the summary script:

```bash
python3 scripts/capstone_summary.py \
  --inject-time "$INJECT_TIME" \
  --rca output/capstone_rca.md
```

Expected output:

```text
═══════════════════════════════════════════════════════════════
  AIOps Capstone — Full Incident Lifecycle
═══════════════════════════════════════════════════════════════

  [1] Inject       ✅  07:00:00Z — WAL archive growth drill started
  [2] Detect       ✅  07:01:28Z — Anomaly score > 70 (TTD: 1m 28s)
  [3] Correlate    ✅  07:02:10Z — 3 alerts correlated to root alert
  [4] Forecast     ✅  07:02:35Z — Disk 100% predicted at 08:18:00Z
  [5] LLM RCA      ✅  07:02:55Z — RCA report generated (21 seconds)
  [6] Remediate    ✅  07:03:40Z — clear-logs.yml completed
  [7] Verify       ✅  07:04:10Z — All layers healthy (TTR: 4m 10s)
  [8] Post-Mortem  ✅  capstone-post-mortem.md complete

  ─────────────────────────────────────────────────────────────
  TTD:  1m 28s ✅ (target: < 2 minutes)
  TTR:  4m 10s ✅ (target: < 10 minutes)
  ─────────────────────────────────────────────────────────────
  Modules used: 5, 7, 8, 9, 10, 11
  All steps complete: ✅
═══════════════════════════════════════════════════════════════
```

---

## Completion Criteria

- [ ] Drill injected; baseline metrics recorded before injection.
- [ ] Anomaly detection fired (disk score > 70); TTD recorded.
- [ ] Alert correlation identified the cascade from disk → DB → app → user.
- [ ] Forecast predicted exhaustion with R² > 0.90.
- [ ] LLM generated an RCA with no hallucinated metrics; reviewed by student.
- [ ] Ansible playbook ran and disk recovered below 30%.
- [ ] All three layers verified healthy after remediation.
- [ ] Blameless post-mortem written with all sections complete and action items owned.
- [ ] `capstone_summary.py` shows all 8 steps ✅.
