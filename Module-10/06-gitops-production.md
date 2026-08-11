# 06 — GitOps & Production Patterns

This final lesson covers GitOps principles, human-in-the-loop policies, advanced auto-remediation patterns, and your Module 10 deliverables. By the end, you will understand not just how to automate remediation but how to govern it safely in production.

---

## GitOps: Git as the Single Source of Truth

GitOps is an operational model where:

1. **Desired state** is stored in Git (infrastructure config, flag state, playbook definitions).
2. **Actual state** is continuously reconciled to match the desired state.
3. **Changes** happen via pull requests — reviewed, approved, and traceable.
4. **Automation** reads from Git, never mutates state outside of a Git commit.

```text
Engineer proposes change → Pull Request → Review & Approve → Merge to main
                                                                    │
                                                          ArgoCD / Flux detects drift
                                                                    │
                                                          Applies change to cluster
                                                                    │
                                                          Reports status back to Git
```

### GitOps Tools

| Tool | Model | Best For |
|---|---|---|
| **ArgoCD** | Pull-based (cluster pulls from Git) | Kubernetes workloads |
| **Flux** | Pull-based (GitOps toolkit) | Kubernetes, multi-tenancy |
| **Ansible AWX** | Push-based (controller pushes to hosts) | VM-based infrastructure |
| **Terraform Cloud** | Plan → Apply workflow | Cloud resource provisioning |

For this module's scope, the key GitOps concept is **storing remediation state in Git** — playbooks, flag configs, and alert rule changes are all committed, not applied manually.

---

## How Auto-Remediation Fits into GitOps

Auto-remediation does not bypass GitOps — it participates in it:

```text
Alert fires → Webhook receiver → Runs playbook from Git
                                        │
                              Log result to file / API
                                        │
                              Open pull request with:
                                - What ran
                                - The outcome
                                - Metric before/after
                                        │
                              Human reviews (for audit, not approval)
```

The playbooks themselves must live in Git:

```text
infra-repo/
  playbooks/
    restart-service.yml    ← version controlled
    clear-logs.yml         ← version controlled
    scale-up.yml           ← version controlled
  flags/
    config.yml             ← flag state in Git
  rules/
    remediation.yml        ← alert rules in Git
```

Never run a playbook that is not committed to the repository. An uncommitted playbook cannot be reviewed, audited, or rolled back.

---

## Human-in-the-Loop Policies

Not every alert should trigger automatic remediation. The following framework helps you decide:

### The Automation Suitability Matrix

| Criterion | Points if YES |
|---|---|
| The same fix has been applied manually 3+ times | +2 |
| The fix has a 95%+ success rate historically | +2 |
| The fix is reversible (can be undone) | +2 |
| The blast radius is limited to one service | +1 |
| No data is deleted or modified | +1 |
| The alert fires in isolation (not during an incident) | +1 |

| Score | Decision |
|---|---|
| 8–9 | ✅ Fully automate |
| 5–7 | ⚠️ Automate with verification and rollback |
| 3–4 | 🔔 Send to human approval queue |
| 0–2 | 🚫 Human-only — never automate |

### Scenarios That Must Remain Human-Only

| Scenario | Why |
|---|---|
| Database deletion or truncation | Irreversible data loss |
| Scaling down instances during traffic peak | May drop production requests |
| Security incident response | Attacker may be actively observing |
| First occurrence of a novel alert in production | Unknown blast radius |
| Cascading failure affecting multiple services | Requires holistic diagnosis |
| Alerts during a change window (deploy in progress) | Change may be the cause |

The last row is particularly important: if a deployment is in progress when an alert fires, the alert is almost certainly caused by the deployment. Auto-remediation that restarts services during a deployment can mask the root cause and extend the incident.

---

## Advanced Remediation Patterns

### Pattern 1: Exponential Backoff for Retries

If a playbook fails, do not retry immediately. Use exponential backoff:

```python
def run_with_retry(playbook: str, max_retries: int = 3):
    for attempt in range(max_retries):
        result = run_playbook(playbook)
        if result == "success":
            return "success"
        wait = 2 ** attempt * 10  # 10s, 20s, 40s
        time.sleep(wait)
    _escalate_to_human(playbook, "Max retries exceeded")
    return "escalated"
```

### Pattern 2: Alert Deduplication

Multiple identical alerts may fire within the same group_interval. Deduplicate by `groupKey`:

```python
_seen_group_keys = set()

def is_duplicate(group_key: str) -> bool:
    if group_key in _seen_group_keys:
        return True
    _seen_group_keys.add(group_key)
    return False
```

Clear `_seen_group_keys` when the alert resolves.

### Pattern 3: Concurrent Alert Protection

If `DiskAlmostFull` and `HighCPULoad` fire simultaneously, run their playbooks in parallel but do not let `scale-up.yml` run while `clear-logs.yml` is already running (they may conflict on disk I/O):

```python
import threading

_playbook_locks = {
    "clear-logs.yml": threading.Lock(),
    "restart-service.yml": threading.Lock(),
    "scale-up.yml": threading.Lock(),
}

def run_remediation_safe(playbook, ...):
    lock = _playbook_locks[playbook]
    if not lock.acquire(blocking=False):
        _log("SKIPPED", ..., outcome="already-running")
        return
    try:
        _run_remediation(playbook, ...)
    finally:
        lock.release()
```

### Pattern 4: Remediation Rate Limiting

Protect against runaway remediation loops — if a playbook runs more than 3 times in 10 minutes, stop and escalate:

```python
from collections import deque

_remediation_times: dict[str, deque] = {}

def _rate_limit_check(playbook: str, max_runs: int = 3, window_sec: int = 600) -> bool:
    """Return True if the playbook should be skipped due to rate limiting."""
    now = time.time()
    times = _remediation_times.setdefault(playbook, deque())
    # Drop old entries outside the window
    while times and times[0] < now - window_sec:
        times.popleft()
    if len(times) >= max_runs:
        return True  # Rate limit hit
    times.append(now)
    return False
```

---

## Governance and Review Cadence

| Frequency | What to Review |
|---|---|
| Daily | Remediation log — any unexpected playbooks running? |
| Weekly | Playbook success rates — which playbooks are failing? |
| Monthly | Automation suitability matrix — what new alerts should be automated? |
| Quarterly | Game day results — what failure scenarios are not covered? |

### Remediation Dashboard

The lab exposes a summary dashboard at `http://localhost:5001/api/remediation-log`. Build a weekly report from it:

```bash
python3 scripts/remediation_report.py --days 7
```

```text
═══════════════════════════════════════════════════════════════
  Auto-Remediation Weekly Report — 2026-08-04 to 2026-08-11
═══════════════════════════════════════════════════════════════
  Total remediations:    23
  Successful:            19  (82.6%)
  Failed:                 2   (8.7%)
  Rolled back:            1   (4.3%)
  Escalated to human:     1   (4.3%)

  By playbook:
    clear-logs.yml      14 runs  |  13 success  |  1 rolled-back
    restart-service.yml  6 runs  |  6  success
    scale-up.yml         3 runs  |  2  success  |  1 failed

  MTTR with automation: 1m 42s (manual baseline: 18m 30s)
  Time saved this week: ~5.5 hours of on-call time
═══════════════════════════════════════════════════════════════
```

---

## Student Deliverables

### Deliverable 1: Ansible Playbook Evidence

Submit for each of the three playbooks:
- The playbook YAML file
- Terminal output showing `PLAY RECAP` with `failed=0`
- The verify step confirming the metric recovered

### Deliverable 2: Webhook End-to-End Evidence

Submit:
- A screenshot or log of the Alertmanager webhook being received
- The remediation log showing STARTED → SUCCESS for `DiskAlmostFull`
- The disk metric before (>85%) and after (<80%) the playbook ran

### Deliverable 3: Chaos Engineering Report

For each of the three experiments:
- Inject time
- TTD (Time to Detect)
- TTR (Time to Recover)
- Whether auto-remediation succeeded or required manual intervention
- One observation about what the experiment revealed

### Deliverable 4: Feature Flag Rollback Evidence

Submit:
- The flag state before the error spike (enabled, 100%)
- The Alertmanager alert that triggered rollback
- The flag state after auto-rollback (disabled, `disabled_reason` populated)
- The error rate before and after rollback

### Deliverable 5: Human-in-the-Loop Policy

Write a one-page policy for your team:
- List 3 scenarios from your own infrastructure that are safe to automate (score ≥ 5)
- List 2 scenarios that must always require human approval (score ≤ 2)
- Define your playbook acceptance criteria (test success rate, documentation, rollback procedure)

---

## Module Summary

You can now write Ansible playbooks for the three most common remediation tasks, wire Alertmanager webhooks to trigger them automatically, run chaos engineering experiments to measure TTD and TTR, implement feature flag auto-rollback on anomaly detection, and apply GitOps principles to govern the entire system. Combined with Modules 7–9, you have the complete AIOps operations stack:

| Module | Capability |
|---|---|
| Module 7 | Detect: SLOs, error budgets, alerting |
| Module 8 | Diagnose: log analytics, incident correlation |
| Module 9 | Prevent: predictive maintenance, capacity forecasting |
| Module 10 | Heal: auto-remediation, chaos engineering, GitOps |

The complete loop: **predict → prevent → detect → diagnose → heal → learn**.

In Module 11, you will apply machine learning to anomaly detection — moving beyond the static thresholds and linear models of Modules 9–10 to systems that learn what "normal" looks like and alert on deviations without requiring manual threshold tuning.
