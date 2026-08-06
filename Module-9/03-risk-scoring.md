# 03 — Infrastructure Risk Scoring

A single metric—disk at 85%—tells you one dimension. But is the system actually at risk? If CPU is at 20%, memory at 30%, and error rate at 0%, the answer is "probably not yet." A **composite risk score** combines multiple metrics into one number that reflects overall system health.

---

## The Risk Score Formula

```text
risk_score = (CPU × w_cpu) + (Memory × w_mem) + (Disk × w_disk) + (ErrorRate × w_err)
```

Default weights:

| Metric | Weight | Rationale |
|---|---|---|
| CPU | 0.20 | Degrades performance but rarely causes immediate outages |
| Memory | 0.20 | Swapping is slow but recoverable |
| Disk | 0.30 | Full disk → write failures → data corruption → outage |
| Error Rate | 0.30 | Direct user impact |

Total weights = 1.0. Each input metric is normalized to 0–100.

---

## Severity Tiers

| Score | Severity | Color | Action |
|---|---|---|---|
| 0–39 | Low | 🟢 Green | Normal operations |
| 40–70 | Medium | 🟡 Yellow | Review capacity, plan remediation |
| 71–100 | High | 🔴 Red | Immediate action required |

---

## The Risk Score Engine

Core logic from `lab/scripts/risk_engine.py`:

```python
from dataclasses import dataclass

@dataclass
class RiskInput:
    cpu: float        # 0–100
    memory: float     # 0–100
    disk: float       # 0–100
    error_rate: float  # 0–100

@dataclass
class RiskResult:
    score: float
    severity: str
    color: str
    breakdown: dict

def calculate_risk(
    inputs: RiskInput,
    weights: dict = None
) -> RiskResult:
    """Calculate composite infrastructure risk score."""
    if weights is None:
        weights = {"cpu": 0.20, "memory": 0.20, "disk": 0.30, "error_rate": 0.30}

    # Clamp inputs to 0–100
    values = {
        "cpu": max(0, min(100, inputs.cpu)),
        "memory": max(0, min(100, inputs.memory)),
        "disk": max(0, min(100, inputs.disk)),
        "error_rate": max(0, min(100, inputs.error_rate)),
    }

    # Weighted composite
    score = sum(values[k] * weights[k] for k in weights)
    score = round(score, 1)

    # Severity classification
    if score < 40:
        severity, color = "Low", "🟢 Green"
    elif score < 71:
        severity, color = "Medium", "🟡 Yellow"
    else:
        severity, color = "High", "🔴 Red"

    breakdown = {k: round(values[k] * weights[k], 1) for k in weights}

    return RiskResult(
        score=score,
        severity=severity,
        color=color,
        breakdown=breakdown,
    )
```

---

## Lab: Score Three Scenarios

### Scenario 1: Healthy System

```python
result = calculate_risk(RiskInput(cpu=25, memory=40, disk=55, error_rate=1))
```

```text
Score: 22.8 — 🟢 Green (Low)
  CPU contribution:        5.0
  Memory contribution:     8.0
  Disk contribution:      16.5
  Error rate contribution:  0.3
```

### Scenario 2: Disk Pressure

```python
result = calculate_risk(RiskInput(cpu=30, memory=45, disk=88, error_rate=5))
```

```text
Score: 42.9 — 🟡 Yellow (Medium)
  CPU contribution:        6.0
  Memory contribution:     9.0
  Disk contribution:      26.4
  Error rate contribution:  1.5
```

### Scenario 3: Cascading Failure

```python
result = calculate_risk(RiskInput(cpu=85, memory=90, disk=97, error_rate=45))
```

```text
Score: 78.6 — 🔴 Red (High)
  CPU contribution:       17.0
  Memory contribution:    18.0
  Disk contribution:      29.1
  Error rate contribution: 13.5
```

---

## Run the Lab

```bash
cd Module-9/lab
python3 scripts/risk_engine.py
```

The script runs all three scenarios and outputs a formatted risk report. It also generates a bar chart comparing the scenarios in `output/risk_comparison.png`.

### Live Risk Score

The lab's Flask app exposes a `/api/risk` endpoint that calculates the risk score from live Prometheus-style metrics:

```bash
curl -s http://localhost:5000/api/risk | python3 -m json.tool
```

```json
{
  "score": 34.2,
  "severity": "Low",
  "color": "Green",
  "breakdown": {
    "cpu": 5.4,
    "memory": 8.0,
    "disk": 15.6,
    "error_rate": 5.2
  },
  "timestamp": "2026-08-06T14:30:00Z"
}
```

---

## Customizing Weights

Different systems have different risk profiles:

| System Type | CPU | Memory | Disk | Error Rate |
|---|---|---|---|---|
| Database server | 0.15 | 0.15 | **0.45** | 0.25 |
| API gateway | **0.30** | 0.20 | 0.10 | **0.40** |
| ML training node | **0.35** | **0.35** | 0.20 | 0.10 |
| Default | 0.20 | 0.20 | 0.30 | 0.30 |

A database server's risk is dominated by disk; an API gateway's risk is dominated by error rate and CPU.

---

## Connecting Risk Scores to Alerts

In production, the risk score feeds into your alerting pipeline:

```text
Risk Score > 70 for 5 minutes → Page: "System risk is RED"
Risk Score > 40 for 15 minutes → Ticket: "System risk is YELLOW — review capacity"
Risk Score trend increasing for 7 days → Predictive: "Risk score will reach RED in 3 days"
```

This ties the risk engine back to the forecasting engine from the previous lesson: you can forecast the risk score itself.

---

## Debrief

- What happens if you set all weights to 0.25? Does it change the severity for any scenario?
- Why is error rate weighted at 0.30 instead of 0.25?
- How would you handle a metric that is temporarily unavailable (e.g., the exporter is down)?
- Could you add a fifth metric (e.g., network latency)? How would you redistribute the weights?

---

## Validation Checklist

- [ ] Risk engine calculates correct scores for all three scenarios.
- [ ] Severity tiers match: Green < 40, Yellow 40–70, Red > 70.
- [ ] Breakdown shows individual metric contributions.
- [ ] Live `/api/risk` endpoint returns a real-time score.
- [ ] Risk comparison chart saved to `output/risk_comparison.png`.
