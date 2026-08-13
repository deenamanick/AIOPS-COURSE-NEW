# 02 — Data Collection & Baselines

Before you can build a Markov model, you need historical data classified into discrete states. This lesson teaches you to generate realistic infrastructure metrics, map them to operational states, and produce the `state_log.csv` that feeds the transition matrix builder.

---

## The Problem

Raw infrastructure metrics are continuous numbers: CPU at 73.2%, memory at 61.8%, error rate at 3.1%. A Markov chain needs **discrete states**: Healthy, Degraded, Critical, Failed. You need a mapping function that converts continuous metrics to categorical states consistently.

---

## State Mapping Rules

The mapping function examines all metrics for a given time window and assigns the **worst** state:

```text
if error_rate > 50%                         → Failed
elif cpu > 80% or mem > 80% or disk > 90%   → Critical
elif cpu > 60% or mem > 60% or disk > 75%   → Degraded
else                                        → Healthy
```

This "worst of" approach is conservative: if CPU is Healthy but memory is Critical, the overall state is Critical. In production, you might assign states per-component instead.

---

## Step 1: Generate Synthetic Historical Data

The lab includes a data generator that creates 30 days of realistic metrics:

```bash
cd Module-13/lab
python3 scripts/generate_state_data.py
```

This produces two files in `data/`:

```text
data/raw_metrics.csv     — continuous metrics (720 rows, one per hour for 30 days)
data/state_log.csv       — discrete states mapped from the raw metrics
```

### Raw Metrics Format

```csv
timestamp,cpu,mem,disk,error_rate
2026-07-01T00:00:00,32.1,45.3,22.0,0.01
2026-07-01T01:00:00,34.5,44.8,22.1,0.02
...
```

### State Log Format

```csv
timestamp,cpu,mem,disk,error_rate,state
2026-07-01T00:00:00,32.1,45.3,22.0,0.01,Healthy
2026-07-01T01:00:00,34.5,44.8,22.1,0.02,Healthy
...
2026-07-15T14:00:00,72.3,65.1,78.2,0.08,Degraded
...
2026-07-22T03:00:00,88.1,82.4,91.0,0.25,Critical
```

---

## Step 2: Understand the Data Generator

Core logic from `scripts/generate_state_data.py`:

```python
def generate_metrics(days=30, points_per_day=24):
    """Generate realistic infrastructure metrics with natural patterns."""
    data = []
    base_date = datetime(2026, 7, 1)

    for i in range(days * points_per_day):
        hour = i % 24
        day = i // 24
        timestamp = base_date + timedelta(hours=i)

        # Base values with daily patterns (higher during business hours)
        business_boost = 15 if 9 <= hour <= 17 else 0
        cpu = 30 + business_boost + random.gauss(0, 8)

        # Inject degradation events (every ~5 days for a few hours)
        if day % 5 == 0 and 10 <= hour <= 14:
            cpu += 35
            mem += 25

        # Inject a critical window (day 22, simulating a real incident)
        if day == 22 and 2 <= hour <= 6:
            cpu = 85 + random.gauss(0, 5)
            error_rate = 0.3 + random.uniform(0, 0.25)

        data.append({...})
    return data
```

The generator creates realistic patterns:
- **Daily cycles**: higher CPU during business hours
- **Periodic degradation**: every ~5 days, simulating batch jobs or deployments
- **A critical incident window**: on day 22, simulating a real production event
- **Noise**: Gaussian noise on all metrics for realism

---

## Step 3: Validate the State Distribution

After generating the data, check the distribution of states:

```bash
python3 scripts/generate_state_data.py --stats
```

Expected output:

```text
═══════════════════════════════════════════════════════════════
  State Distribution (30 days, 720 data points)
═══════════════════════════════════════════════════════════════
  Healthy:   542 (75.3%)  ████████████████████████████████░░░░░░░░
  Degraded:  118 (16.4%)  ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  Critical:   48 (6.7%)   ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  Failed:     12 (1.7%)   █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
═══════════════════════════════════════════════════════════════
```

A healthy system should spend most time in Healthy (>70%) with occasional degradation. If your distribution looks very different, adjust the thresholds.

---

## Step 4: Examine State Transitions

Look at the raw transitions in the state log:

```bash
# Count transitions
python3 -c "
import csv
from collections import Counter

with open('data/state_log.csv') as f:
    states = [row['state'] for row in csv.DictReader(f)]
transitions = Counter(zip(states, states[1:]))
for (s1, s2), count in transitions.most_common():
    print(f'  {s1:10s} → {s2:10s}: {count:4d}')
"
```

Expected patterns:
- **Healthy → Healthy** should be the most common (system is stable most of the time)
- **Degraded → Healthy** should be frequent (most degradations self-resolve)
- **Critical → Failed** should be relatively rare (not every critical event leads to failure)
- **Failed → Healthy** should exist (auto-remediation from Module 10)

---

## Mapping Functions: Alternatives

The simple threshold approach works for training. In production, consider:

| Approach | Pros | Cons |
|---|---|---|
| **Threshold-based** (our approach) | Simple, interpretable, fast | Requires manual tuning per service |
| **K-Means clustering** | Learns states from data | States may not align with operational meaning |
| **Percentile-based** | Adapts to each service's baseline | Needs enough historical data |
| **SLO-based** | Directly maps to business objectives | Requires well-defined SLOs |

---

## Validation Checklist

- [ ] `raw_metrics.csv` generated with 720 rows (30 days × 24 hours).
- [ ] `state_log.csv` generated with state column added.
- [ ] State distribution printed and reviewed (Healthy should dominate).
- [ ] Transition patterns examined—self-transitions should be most common.
- [ ] Understand the mapping function thresholds and how to adjust them.

In the next lesson, you'll take this state log and build the transition matrix.
