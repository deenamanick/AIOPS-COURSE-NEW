# 04 — Predictive Forecasting & Automation

This lesson connects the transition matrix to real-time prediction. You'll compute the probability of reaching the **Failed** state within a configurable time horizon, and if the probability exceeds 60%, trigger a webhook to an Ansible auto-remediation playbook.

---

## The Problem

You know the current state is **Critical**. The transition matrix tells you there's a 27.6% chance of failure in the next time step. But what about the next 6 time steps (30 minutes if each step is 5 minutes)? The cumulative probability is higher—and that's what you need for actionable prediction.

---

## N-Step Forecasting

### The Math

```text
state_vector(t + N) = state_vector(t) × P^N
```

Where:
- `state_vector(t)` is a 1×4 vector representing the current state (e.g., `[0, 0, 1, 0]` for Critical)
- `P` is the 4×4 transition matrix
- `P^N` is the matrix raised to the Nth power (matrix multiplication N times)

### Step-by-Step Example

Starting from **Critical**, forecast over 6 steps:

```text
Step 0: [0.000, 0.000, 1.000, 0.000]  → P(Failed) =  0.0%  (now)
Step 1: [0.086, 0.172, 0.466, 0.276]  → P(Failed) = 27.6%
Step 2: [0.101, 0.166, 0.340, 0.393]  → P(Failed) = 39.3%
Step 3: [0.111, 0.159, 0.271, 0.459]  → P(Failed) = 45.9%
Step 4: [0.118, 0.153, 0.228, 0.501]  → P(Failed) = 50.1%
Step 5: [0.122, 0.148, 0.200, 0.530]  → P(Failed) = 53.0%
Step 6: [0.125, 0.144, 0.181, 0.550]  → P(Failed) = 55.0%
```

At step 6, there's a 55% chance of being in the Failed state. If the threshold is 60%, no webhook fires yet. But at step 8:

```text
Step 8: [0.129, 0.139, 0.157, 0.575]  → P(Failed) = 57.5%
Step 9: [0.130, 0.137, 0.149, 0.584]  → P(Failed) = 58.4%
Step 10:[0.131, 0.135, 0.143, 0.591]  → P(Failed) = 59.1%
Step 11:[0.132, 0.134, 0.139, 0.595]  → P(Failed) = 59.5%  still below
Step 12:[0.132, 0.134, 0.136, 0.598]  → P(Failed) = 59.8%  still below
Step 13:[0.133, 0.133, 0.133, 0.601]  → P(Failed) = 60.1%  ⚠️ THRESHOLD!
```

At step 13 (65 minutes at 5-min intervals), the threshold is crossed.

---

## Step 1: Run the Forecasting Engine

```bash
cd Module-13/lab
python3 scripts/forecast.py --state Critical --matrix data/transition_matrix.csv
```

Expected output:

```text
═══════════════════════════════════════════════════════════════
  Markov Chain Failure Forecast
═══════════════════════════════════════════════════════════════
  Current state:     Critical
  Time step:         5 minutes
  Forecast horizon:  6 steps (30 minutes)
  Threshold:         60%

  Step-by-Step Forecast:
    Step 1:  P(Failed) = 27.6%
    Step 2:  P(Failed) = 39.3%
    Step 3:  P(Failed) = 45.9%
    Step 4:  P(Failed) = 50.1%
    Step 5:  P(Failed) = 53.0%
    Step 6:  P(Failed) = 55.0%

  Final P(Failed) at step 6: 55.0%
  ✅ Below threshold (60%). No remediation triggered.
═══════════════════════════════════════════════════════════════
```

Try with more steps:

```bash
python3 scripts/forecast.py --state Critical --matrix data/transition_matrix.csv --steps 13
```

```text
  Final P(Failed) at step 13: 60.1%
  ⚠️ THRESHOLD EXCEEDED — Triggering remediation webhook!
  📡 POST http://localhost:5001/ansible-trigger
  ✅ Webhook delivered successfully
═══════════════════════════════════════════════════════════════
```

---

## Step 2: Understanding the Forecast Script

Core logic from `scripts/forecast.py`:

```python
def forecast_failure(matrix: np.ndarray, states: list, start_state: str,
                     steps: int) -> list[dict]:
    """Compute state distribution at each step via matrix multiplication."""
    vec = np.zeros(len(states))
    vec[states.index(start_state)] = 1.0
    failed_idx = states.index("Failed")

    results = []
    for step in range(1, steps + 1):
        vec = vec @ matrix
        results.append({
            "step": step,
            "distribution": dict(zip(states, vec)),
            "p_failed": float(vec[failed_idx]),
        })
    return results
```

The function is pure NumPy—no loops over matrix elements, just repeated matrix-vector multiplication. For a 4×4 matrix, this runs in microseconds even for 1000 steps.

---

## Step 3: Configure the Threshold and Webhook

The forecast script has three tunable parameters:

| Parameter | Default | Environment Variable | Description |
|---|---|---|---|
| Steps | 6 | `MARKOV_STEPS` | Number of time steps to forecast |
| Threshold | 0.60 | `MARKOV_THRESHOLD` | P(Failed) threshold for triggering action |
| Webhook URL | `http://localhost:5001/ansible-trigger` | `WEBHOOK_URL` | Where to POST the remediation payload |

Override via CLI:

```bash
python3 scripts/forecast.py \
  --state Critical \
  --matrix data/transition_matrix.csv \
  --steps 10 \
  --threshold 0.50 \
  --webhook http://your-ansible-endpoint:5001/ansible-trigger
```

---

## Step 4: The Webhook Payload

When the threshold is exceeded, the script sends a JSON payload:

```json
{
  "source": "markov-forecaster",
  "current_state": "Critical",
  "p_failed": 0.601,
  "threshold": 0.60,
  "steps": 13,
  "time_horizon_minutes": 65,
  "recommended_action": "scale-up",
  "timestamp": "2026-08-06T14:35:00Z"
}
```

This integrates directly with the Module 10 webhook receiver. The `recommended_action` field maps to playbook names: `restart-service`, `clear-logs`, `scale-up`.

---

## Step 5: Forecast from Every State

Run the forecast for all four starting states to build intuition:

```bash
for state in Healthy Degraded Critical Failed; do
  python3 scripts/forecast.py --state $state --matrix data/transition_matrix.csv --steps 6 --quiet
done
```

```text
  Healthy  → P(Failed) at step 6:  3.2%  ✅
  Degraded → P(Failed) at step 6: 28.4%  ✅
  Critical → P(Failed) at step 6: 55.0%  ✅ (close to threshold)
  Failed   → P(Failed) at step 6: 72.1%  ⚠️ WEBHOOK TRIGGERED
```

Key insight: even the Failed state doesn't have P(Failed) = 100% at step 6, because the transition matrix includes recovery paths (Module 10 auto-remediation).

---

## Connecting the Pipeline

```text
Module 6:  Prometheus scrapes metrics every 15s
Module 7:  Alertmanager detects threshold breach → fires alert
Module 9:  Linear regression predicts WHEN a metric hits a limit
Module 13: Markov chain predicts WHAT STATE the system will be in
Module 10: Ansible playbook executes the remediation

           ┌─────────────────────────────────────────────────┐
           │         Complete Predictive Pipeline            │
           │                                                 │
           │  Metrics → State Mapper → Markov → Webhook →   │
           │  Ansible → Recovery → Verify → Log             │
           └─────────────────────────────────────────────────┘
```

---

## Validation Checklist

- [ ] Forecast run from each starting state (Healthy, Degraded, Critical, Failed).
- [ ] Step-by-step probabilities match matrix multiplication (verify manually for step 1).
- [ ] Threshold correctly triggers webhook when exceeded.
- [ ] Webhook payload includes all required fields.
- [ ] Understand the relationship between step count, time horizon, and threshold.
- [ ] CLI arguments work: `--state`, `--steps`, `--threshold`, `--webhook`.

In the next lesson, you'll run a live break/fix drill where you inject load and watch the full pipeline operate in real time.
