# 05 — Break/Fix: Predictive Alerting

This is the capstone exercise for Module 9. You will inject a steady disk growth pattern into the lab, run the forecasting model, verify it predicts the correct exhaustion time, set a predictive alert that fires before the actual failure, and confirm the alert triggers early enough to prevent an outage.

---

## The Scenario

A database server accumulates write-ahead logs at a steady rate. Disk usage grows approximately 1 GB per hour on a 10 GB volume. At this rate, the disk fills in approximately 8 hours. Your job is to predict this before it happens and alert 2 hours early.

---

## Step 1: Establish the Baseline

```bash
cd Module-9/lab
docker compose up -d --build
```

Check the current simulated disk usage:

```bash
curl -s http://localhost:5000/api/metrics | python3 -m json.tool
```

```json
{
  "disk_usage_pct": 20.0,
  "cpu_usage_pct": 25.3,
  "memory_usage_pct": 42.1,
  "error_rate_pct": 0.5,
  "timestamp": "2026-08-06T14:00:00Z"
}
```

Risk score should be Green:

```bash
curl -s http://localhost:5000/api/risk | python3 -m json.tool
```

---

## Step 2: Start the Disk Growth Injection

```bash
curl -X POST http://localhost:5000/drill/disk-growth
```

This activates a simulated growth pattern:

- Starting value: current disk usage (~20%)
- Growth rate: ~10% per hour (accelerated for training; real-world would be 1 GB/hr on a 10 GB volume)
- At this rate, the disk reaches 100% in approximately 8 hours

The drill uses an accelerated clock: 1 real minute = 1 simulated hour. This means the full 8-hour lifecycle plays out in 8 minutes during training.

---

## Step 3: Collect Forecast Data

The app emits a data point every 10 seconds (simulating hourly reads). Collect data for 3 simulated hours (3 real minutes):

```bash
python3 scripts/collect_live.py --duration 180 --output data/live_disk.csv
```

This produces:

```csv
date,value
2026-08-06T14:00:00Z,20.0
2026-08-06T15:00:00Z,30.2
2026-08-06T16:00:00Z,40.1
```

---

## Step 4: Run the Forecast

```bash
python3 scripts/forecast.py --input data/live_disk.csv --limit 100
```

Expected output:

```text
═══════════════════════════════════════════════════════════════
  Live Disk Usage Forecast
═══════════════════════════════════════════════════════════════
  Data points:       18
  Current value:     40.1%
  Growth rate:       +10.1%/hour
  Hours to 100%:     5.9 hours
  Predicted time:    2026-08-06T21:54:00Z
  R² score:          0.98

  🚨 PREDICTIVE ALERT: Disk will exhaust in < 6 hours!
  ⏰ Recommended alert time: 2026-08-06T19:54:00Z (2 hours before)
═══════════════════════════════════════════════════════════════
```

A forecast plot is saved to `output/live_disk_forecast.png`.

---

## Step 5: Set the Predictive Alert

The lab includes a simple alert scheduler:

```bash
python3 scripts/set_predictive_alert.py \
  --metric disk \
  --predicted-exhaustion "2026-08-06T21:54:00Z" \
  --lead-time-hours 2
```

Output:

```text
[ALERT SCHEDULER] Predictive alert set:
  Metric:            disk
  Predicted failure:  2026-08-06T21:54:00Z
  Alert fires at:     2026-08-06T19:54:00Z (2h before predicted failure)
  Status:            ARMED ✅
```

---

## Step 6: Wait for the Alert

Continue the simulation and watch for the alert:

```bash
docker compose logs -f app
```

At the accelerated rate, you should see within ~6 real minutes:

```text
[PREDICTIVE-ALERT] 🚨 FIRING: Disk predicted to exhaust at 21:54:00Z
[PREDICTIVE-ALERT]    Current: 80.2% | Rate: +10.1%/hr | ETA: 1h 58m
[PREDICTIVE-ALERT]    Action: Expand volume or clean WAL files NOW
```

---

## Step 7: Verify the Prediction

Let the simulation continue to exhaustion (do NOT reset the drill). When the disk simulation hits 100%:

```text
[DRILL] Disk simulation reached 100% at 2026-08-06T21:56:00Z
[DRILL] Predicted: 21:54:00Z | Actual: 21:56:00Z | Error: 2 minutes (0.4%)
```

A prediction within 5% of the actual time is considered accurate for linear models.

---

## Step 8: Reset and Report

```bash
curl -X POST http://localhost:5000/drill/reset
```

Write a brief report:

```markdown
## Predictive Alerting Report

**Metric:** Disk usage
**Growth pattern:** Linear, ~10%/hr
**Predicted exhaustion:** 21:54:00Z
**Actual exhaustion:** 21:56:00Z
**Prediction error:** 2 minutes (0.4%)
**Alert fired at:** 19:54:00Z (2 hours before predicted failure)
**Time to act:** 2 hours — sufficient to expand volume

**Conclusion:** The linear regression model accurately predicted
disk exhaustion within 0.4% of actual time. The predictive alert
fired 2 hours early, providing adequate response time.
```

---

## Connecting Modules 7–9

| Module | What You Learn | Role in Production |
|---|---|---|
| Module 7 | Alerting & SRE | **Reactive**: detect and respond to failures |
| Module 8 | Log Analytics & Correlation | **Diagnostic**: understand why failures happen |
| Module 9 | Predictive Maintenance | **Proactive**: prevent failures before they happen |

Together, these three modules form the complete AIOps operations lifecycle: predict → prevent → detect → correlate → respond → recover.

---

## Completion Criteria

- [ ] Disk growth drill activated and data collected.
- [ ] Forecast correctly predicted exhaustion within 5% accuracy.
- [ ] Predictive alert set with a 2-hour lead time.
- [ ] Alert fired before the simulated exhaustion.
- [ ] Prediction vs actual comparison documented.
- [ ] Report written with timeline, accuracy, and conclusion.
