# 04 — DORA Metrics & Engineering Performance

DORA (DevOps Research and Assessment) identified four metrics that predict how well an engineering team delivers software. Unlike infrastructure metrics that measure machines, DORA metrics measure **teams**. In this lesson, you will calculate all four from real GitHub Actions data.

---

## The Four DORA Metrics

| Metric | What It Measures | How to Calculate |
|---|---|---|
| **Deployment Frequency** | How often code reaches production | Count of production deployments per time period |
| **Lead Time for Changes** | Time from commit to production | Median time between first commit and deployment |
| **Change Failure Rate** | % of deployments that cause failures | Failed deployments ÷ total deployments × 100 |
| **MTTR** (Mean Time to Restore) | Time to recover from a failure | Median time between failure detection and service restoration |

---

## DORA Performance Tiers

| Tier | Deploy Frequency | Lead Time | Change Failure Rate | MTTR |
|---|---|---|---|---|
| 🏆 Elite | Multiple per day | < 1 hour | 0–15% | < 1 hour |
| 🟢 High | Daily to weekly | 1 day – 1 week | 16–30% | < 1 day |
| 🟡 Medium | Weekly to monthly | 1 week – 1 month | 16–30% | 1 day – 1 week |
| 🔴 Low | Monthly+ | 1 month – 6 months | 16–30% | 1 week – 1 month |

Elite teams deploy frequently, deliver fast, break less, and recover quickly. These are not aspirational ideals—they are measured outcomes from thousands of organizations.

---

## Data Source: GitHub Actions

GitHub Actions workflow runs contain everything needed:

```bash
# Fetch the last 100 workflow runs for a repository
gh api repos/{owner}/{repo}/actions/runs?per_page=100 \
  --jq '.workflow_runs[] | {
    id: .id,
    name: .name,
    status: .status,
    conclusion: .conclusion,
    created_at: .created_at,
    updated_at: .updated_at,
    head_sha: .head_sha,
    event: .event
  }' > workflow_runs.json
```

For this lab, a pre-generated dataset is provided in `data/workflow_runs.csv`:

```csv
run_id,workflow,conclusion,created_at,completed_at,event,head_sha
12345,deploy.yml,success,2026-07-01T10:00:00Z,2026-07-01T10:05:00Z,push,abc123
12346,deploy.yml,failure,2026-07-03T14:30:00Z,2026-07-03T14:35:00Z,push,def456
12347,deploy.yml,success,2026-07-03T16:00:00Z,2026-07-03T16:04:00Z,push,ghi789
```

---

## Lab: Calculate DORA Metrics

```bash
cd Module-9/lab
python3 scripts/dora_calculator.py
```

### Metric 1: Deployment Frequency

```python
def deployment_frequency(deploys: list, days: int) -> dict:
    """Count successful production deployments per week."""
    successful = [d for d in deploys if d["conclusion"] == "success"]
    per_day = len(successful) / max(days, 1)
    per_week = per_day * 7

    if per_day >= 1:
        tier = "Elite"
    elif per_week >= 1:
        tier = "High"
    elif per_week >= 0.25:  # ~monthly
        tier = "Medium"
    else:
        tier = "Low"

    return {"per_day": round(per_day, 2), "per_week": round(per_week, 2), "tier": tier}
```

### Metric 2: Lead Time for Changes

```python
from datetime import datetime

def lead_time(deploys: list) -> dict:
    """Median time from commit creation to deployment completion."""
    durations = []
    for d in deploys:
        if d["conclusion"] == "success":
            created = datetime.fromisoformat(d["created_at"].rstrip("Z"))
            completed = datetime.fromisoformat(d["completed_at"].rstrip("Z"))
            durations.append((completed - created).total_seconds() / 3600)

    if not durations:
        return {"median_hours": None, "tier": "Unknown"}

    median = sorted(durations)[len(durations) // 2]

    if median < 1:
        tier = "Elite"
    elif median < 24:
        tier = "High"
    elif median < 168:  # 1 week
        tier = "Medium"
    else:
        tier = "Low"

    return {"median_hours": round(median, 2), "tier": tier}
```

### Metric 3: Change Failure Rate

```python
def change_failure_rate(deploys: list) -> dict:
    """Percentage of deployments that resulted in failure."""
    total = len(deploys)
    failures = sum(1 for d in deploys if d["conclusion"] == "failure")

    if total == 0:
        return {"rate": 0, "tier": "Unknown"}

    rate = (failures / total) * 100

    if rate <= 15:
        tier = "Elite"
    elif rate <= 30:
        tier = "High/Medium"
    else:
        tier = "Low"

    return {"rate": round(rate, 1), "failures": failures, "total": total, "tier": tier}
```

### Metric 4: Mean Time to Restore (MTTR)

```python
def mttr(deploys: list) -> dict:
    """Median time between a failure and the next successful deployment."""
    restore_times = []
    last_failure_time = None

    for d in sorted(deploys, key=lambda x: x["created_at"]):
        if d["conclusion"] == "failure":
            last_failure_time = datetime.fromisoformat(d["completed_at"].rstrip("Z"))
        elif d["conclusion"] == "success" and last_failure_time:
            restored = datetime.fromisoformat(d["completed_at"].rstrip("Z"))
            restore_times.append((restored - last_failure_time).total_seconds() / 3600)
            last_failure_time = None

    if not restore_times:
        return {"median_hours": None, "tier": "Unknown"}

    median = sorted(restore_times)[len(restore_times) // 2]

    if median < 1:
        tier = "Elite"
    elif median < 24:
        tier = "High"
    elif median < 168:
        tier = "Medium"
    else:
        tier = "Low"

    return {"median_hours": round(median, 2), "tier": tier}
```

---

## Expected Output

```text
═══════════════════════════════════════════════════════════════
  DORA Metrics Report — deenamanick/jeevi-ai-reviewer
  Period: 2026-07-01 to 2026-07-30 (30 days)
═══════════════════════════════════════════════════════════════

  Deployment Frequency:   1.4 / day (9.8 / week)
  Tier: 🏆 Elite

  Lead Time for Changes:  0.08 hours (5 minutes median)
  Tier: 🏆 Elite

  Change Failure Rate:    12.5% (5 failures / 40 deploys)
  Tier: 🏆 Elite

  Mean Time to Restore:   1.5 hours
  Tier: 🟢 High

  ─────────────────────────────────────────────────────────────
  Overall DORA Tier:      🏆 Elite / 🟢 High
  ─────────────────────────────────────────────────────────────
```

The script also generates `output/dora_dashboard.png` with four bar charts comparing your metrics to the DORA benchmarks.

---

## Why DORA Metrics Matter for AIOps

| Connection | How |
|---|---|
| High deployment frequency | More deployments → more data for ML models |
| Low lead time | Fast feedback → faster anomaly resolution |
| Low change failure rate | Fewer incidents → less noise for correlation engines |
| Low MTTR | Fast recovery → smaller error budgets consumed |

DORA metrics are the **input quality** of your AIOps pipeline. A team with elite DORA metrics produces cleaner signals, smaller incidents, and faster recovery—making every AIOps tool more effective.

---

## Validation Checklist

- [ ] All four DORA metrics calculated from the dataset.
- [ ] Each metric classified into the correct performance tier.
- [ ] DORA dashboard plot saved to `output/dora_dashboard.png`.
- [ ] Understood the connection between DORA and AIOps effectiveness.
