# 01 — Self-Healing Patterns

Every incident response follows the same firefighting loop: alert fires, on-call wakes up, engineer logs in, diagnoses, applies fix, verifies, goes back to sleep. At 2 AM. For the fourth time this month. Self-healing systems break that cycle by automating the remediation actions your team applies repeatedly—freeing engineers for work that actually requires human judgment.

---

## The Self-Healing Cycle

```text
DETECT   → Alert fires: DiskAlmostFull, NginxDown, HighCPULoad
VALIDATE → Is this alert real? Is it safe to auto-remediate?
ACT      → Run the Ansible playbook / call the API / scale the container
VERIFY   → Did the remediation work? Is the metric recovering?
ROLLBACK → If verify fails, undo the action and escalate to human
LOG      → Record what happened, when, who (the automation) did it, and why
```

This six-step pattern is the foundation of every production auto-remediation system. Skipping any step creates dangerous automation: acting without validation causes false positives; acting without verification hides broken playbooks; acting without logging creates audit black holes.

---

## Why Automation Fails Without Validation

Consider a naive webhook receiver:

```python
# DANGEROUS — no validation
@app.post("/webhook")
def webhook():
    subprocess.run(["ansible-playbook", "restart-service.yml"])
    return "ok"
```

Problems:
1. A malformed Alertmanager payload still triggers the playbook.
2. A "resolved" alert (alert is now OK) triggers a restart unnecessarily.
3. A `DiskAlmostFull` alert triggers a service restart instead of log cleanup.
4. No record of what ran or why.

The correct pattern adds a validation layer:

```python
@app.post("/webhook")
def webhook():
    payload = request.get_json(force=True)

    # 1. Validate payload structure
    alerts = payload.get("alerts", [])
    if not alerts:
        return jsonify({"status": "skipped", "reason": "no alerts in payload"}), 200

    for alert in alerts:
        # 2. Skip resolved alerts
        if alert.get("status") != "firing":
            continue

        # 3. Route to correct playbook by alert name
        name = alert.get("labels", {}).get("alertname", "")
        run_remediation(name, alert)

    return jsonify({"status": "processed"}), 200
```

---

## The Remediation Decision Tree

```text
Alert received
    │
    ├── status == "resolved"?  → Skip (no action needed)
    │
    ├── alertname == "NginxDown"?
    │       └── Run: restart-service.yml
    │
    ├── alertname == "DiskAlmostFull"?
    │       └── Run: clear-logs.yml
    │
    ├── alertname == "HighCPULoad"?
    │       └── Run: scale-up.yml
    │
    └── Unknown alert → Log and escalate (do NOT auto-remediate unknown alerts)
```

Unknown alerts must never auto-remediate. If you can't predict what the playbook will do, a human must decide.

---

## When NOT to Auto-Remediate

The most important skill in auto-remediation is knowing when to stop. Some actions are too risky to automate:

| Scenario | Risk | Policy |
|---|---|---|
| Deleting files or database records | Data loss — irreversible | Human approval required |
| Scaling **down** instances | May drop in-flight requests | Human approval required |
| Restarting stateful services (databases) | Corruption risk if mid-write | Human approval required |
| Security alerts (unauthorized access) | Attacker may be watching | Human-in-the-loop always |
| First time a new alert fires in production | Unknown blast radius | Manual first run, then automate |

A useful rule of thumb: **automate remediation when you have run the same manual fix at least 3 times with a success rate above 95%.**

---

## The Verify-and-Rollback Pattern

After a playbook runs, the system must confirm the fix worked:

```python
def run_with_verify(playbook: str, verify_fn, rollback_fn, timeout_sec=60):
    """Run a playbook, verify it worked, rollback if it didn't."""
    # Act
    result = subprocess.run(
        ["ansible-playbook", f"playbooks/{playbook}"],
        capture_output=True, text=True, timeout=120
    )

    if result.returncode != 0:
        log_event("FAILED", playbook, result.stderr)
        return "failed"

    # Verify (poll for up to timeout_sec)
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if verify_fn():
            log_event("SUCCESS", playbook, "Metric recovered")
            return "success"
        time.sleep(5)

    # Rollback — verification timed out
    rollback_fn()
    log_event("ROLLED_BACK", playbook, "Metric did not recover within timeout")
    return "rolled-back"
```

The verify function is specific to the playbook:
- `restart-service.yml` → check that the Nginx process is running
- `clear-logs.yml` → check that disk usage dropped below 80%
- `scale-up.yml` → check that a new healthy replica is registered

---

## Logging Every Remediation Action

Every remediation action must be logged with:

| Field | Purpose |
|---|---|
| `timestamp` | When did this happen? |
| `alert_name` | What triggered it? |
| `playbook` | What action was taken? |
| `outcome` | success / failed / rolled-back |
| `duration_sec` | How long did it take? |
| `verify_result` | Did the metric actually recover? |

This log is your **audit trail** for compliance, post-incident review, and playbook improvement.

---

## Connecting Modules 9 and 10

| Module | Layer | Role |
|---|---|---|
| Module 7 | Alerting | Detect: fire the alert |
| Module 8 | Correlation | Diagnose: understand why |
| Module 9 | Prediction | Prevent: catch it before it happens |
| Module 10 | Remediation | Heal: fix it automatically when it does happen |

Together, these four modules form the complete AIOps operations loop: **predict → prevent → detect → diagnose → heal**.

---

## Key Takeaway

Auto-remediation does not eliminate on-call. It eliminates the **repetitive, low-judgment** pages—restarting a service, clearing a log directory, adding a replica. What remains for humans are the novel, high-stakes, high-ambiguity situations that require judgment no playbook can encode.

In the next lesson, you will write the three Ansible playbooks that power the remediation system.
