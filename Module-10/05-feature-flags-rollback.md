# 05 — Feature Flags & Auto-Rollback

A **feature flag** (also called a feature toggle) lets you enable or disable a code path at runtime without deploying new code. They are used to:

- Release features to a subset of users before full rollout
- Instantly disable a feature if it causes errors
- Decouple deployment from release

In the context of AIOps, feature flags are one of the fastest remediation mechanisms available. If anomaly detection fires on a new feature, auto-rollback can disable the flag in milliseconds — no deployment, no Ansible playbook, no on-call engineer required.

---

## The Auto-Rollback Pattern

```text
Deploy → Enable flag → Monitor → Anomaly detected?
                                       │
                                 YES ──┤── POST /flags/{feature}/disable
                                       │         │
                                       │    Flag disabled → Feature off
                                       │         │
                                       │    Verify: error rate drops?
                                       │         │
                                       │    YES ─┘── Log: "Auto-rollback successful"
                                       │    NO  ─┘── Escalate: "Flag disabled but errors persist"
                                 NO  ──┘── Continue monitoring
```

---

## Feature Flag API

The lab app exposes a simple flag API that stores flag state in memory:

```python
# From lab/app/app.py

# Flag store: name -> {enabled, rollout_pct, created_at, disabled_at, disabled_reason}
_flags = {
    "new-checkout-flow": {
        "enabled": True,
        "rollout_pct": 100,
        "created_at": "2026-08-11T06:00:00Z",
        "disabled_at": None,
        "disabled_reason": None,
    },
    "ml-recommendations": {
        "enabled": True,
        "rollout_pct": 20,  # Only 20% of users see this
        "created_at": "2026-08-10T12:00:00Z",
        "disabled_at": None,
        "disabled_reason": None,
    },
    "streaming-export": {
        "enabled": False,
        "rollout_pct": 0,
        "created_at": "2026-08-09T09:00:00Z",
        "disabled_at": "2026-08-09T14:30:00Z",
        "disabled_reason": "High error rate detected during rollout",
    },
}


@app.get("/flags")
def list_flags():
    return jsonify(_flags)


@app.get("/flags/<name>")
def get_flag(name: str):
    flag = _flags.get(name)
    if not flag:
        return jsonify({"error": f"Flag '{name}' not found"}), 404
    return jsonify({name: flag})


@app.post("/flags/<name>/enable")
def enable_flag(name: str):
    body = request.get_json(force=True) or {}
    rollout_pct = body.get("rollout_pct", 100)
    if name not in _flags:
        _flags[name] = {}
    _flags[name].update({
        "enabled": True,
        "rollout_pct": rollout_pct,
        "disabled_at": None,
        "disabled_reason": None,
    })
    return jsonify({"status": "enabled", "flag": name, "rollout_pct": rollout_pct})


@app.post("/flags/<name>/disable")
def disable_flag(name: str):
    body = request.get_json(force=True) or {}
    reason = body.get("reason", "Manual disable")
    if name not in _flags:
        return jsonify({"error": f"Flag '{name}' not found"}), 404
    from datetime import datetime, timezone
    _flags[name].update({
        "enabled": False,
        "rollout_pct": 0,
        "disabled_at": datetime.now(timezone.utc).isoformat(),
        "disabled_reason": reason,
    })
    # Inject the flag disable into state to simulate error rate drop
    if name == "new-checkout-flow":
        _state["error_rate"] = max(0, _state["error_rate"] - 15)
    return jsonify({"status": "disabled", "flag": name, "reason": reason})


@app.post("/flags/rollback")
def rollback_all():
    """Emergency: disable all flags that are currently enabled."""
    from datetime import datetime, timezone
    disabled = []
    for name, flag in _flags.items():
        if flag.get("enabled"):
            flag.update({
                "enabled": False,
                "rollout_pct": 0,
                "disabled_at": datetime.now(timezone.utc).isoformat(),
                "disabled_reason": "Emergency rollback triggered by anomaly detection",
            })
            disabled.append(name)
    return jsonify({"status": "emergency-rollback", "disabled_flags": disabled})
```

---

## Lab: Manual Flag Operations

### List all flags

```bash
curl -s http://localhost:5001/flags | python3 -m json.tool
```

```json
{
  "new-checkout-flow": {
    "enabled": true,
    "rollout_pct": 100,
    "created_at": "2026-08-11T06:00:00Z",
    "disabled_at": null,
    "disabled_reason": null
  },
  "ml-recommendations": {
    "enabled": true,
    "rollout_pct": 20,
    ...
  }
}
```

### Enable a flag at 10% rollout

```bash
curl -X POST http://localhost:5001/flags/new-checkout-flow/enable \
  -H "Content-Type: application/json" \
  -d '{"rollout_pct": 10}'
```

### Disable a specific flag

```bash
curl -X POST http://localhost:5001/flags/new-checkout-flow/disable \
  -H "Content-Type: application/json" \
  -d '{"reason": "High 5xx error rate during rollout"}'
```

### Emergency rollback — disable all flags

```bash
curl -X POST http://localhost:5001/flags/rollback
```

```json
{
  "status": "emergency-rollback",
  "disabled_flags": ["new-checkout-flow", "ml-recommendations"]
}
```

---

## Lab: Auto-Rollback on Anomaly Detection

The anomaly detection trigger is built into the webhook receiver. When the error rate anomaly fires, the receiver checks if a feature flag was recently enabled and disables it automatically.

### Step 1: Enable the flag and inject errors

```bash
# Enable the new checkout flow at 100%
curl -X POST http://localhost:5001/flags/new-checkout-flow/enable \
  -d '{"rollout_pct": 100}' -H "Content-Type: application/json"

# Inject a high error rate to simulate the feature causing 5xx errors
curl -X POST http://localhost:5001/drill/error-spike
```

The `error-spike` drill increases `sim_error_rate_pct` to 35%.

### Step 2: Watch the auto-rollback

The anomaly detection rule in `rules/remediation.yml`:

```yaml
- alert: HighErrorRate
  expr: sim_error_rate_pct > 20
  for: 1m
  labels:
    severity: critical
    auto_remediate: "true"
  annotations:
    summary: "Error rate exceeded 20% — check recent feature flag changes"
```

After 1 minute, Alertmanager fires `HighErrorRate`. The webhook receiver checks the flag store, finds `new-checkout-flow` was recently enabled, and disables it:

```text
[REMEDIATION] STARTED | HighErrorRate | rollback-flag
[REMEDIATION] Disabling flag: new-checkout-flow (enabled 3 minutes ago)
[REMEDIATION] Flag disabled. Verifying error rate recovery...
[REMEDIATION] SUCCESS | HighErrorRate | metric-recovered (28 seconds)
```

### Step 3: Verify

```bash
curl -s http://localhost:5001/flags/new-checkout-flow | python3 -m json.tool
```

```json
{
  "new-checkout-flow": {
    "enabled": false,
    "rollout_pct": 0,
    "disabled_at": "2026-08-11T07:15:28Z",
    "disabled_reason": "Auto-rollback: HighErrorRate anomaly detected. Flag enabled 3 minutes prior."
  }
}
```

---

## Rollout Strategy with Flags

Feature flags enable safe progressive rollout:

| Stage | Rollout % | Action |
|---|---|---|
| Canary | 1–5% | Enable for internal users only |
| Early Access | 10–20% | Enable for beta users |
| Staged Rollout | 50% | Enable for half of production traffic |
| Full Release | 100% | Enable for everyone |
| Rollback | 0% | Disable immediately if anomaly detected |

Auto-rollback is most effective during the early stages (1–20%) where:
- Errors affect a small user population
- The flag is the most recent change
- The correlation between flag enablement and error spike is high

---

## Connecting Feature Flags to GitOps

In production, flag state should live in Git, not in memory:

```yaml
# flags/config.yml (committed to the infrastructure repo)
flags:
  new-checkout-flow:
    enabled: true
    rollout_pct: 20
  ml-recommendations:
    enabled: false
    rollout_pct: 0
```

Auto-rollback commits a change to `flags/config.yml` and opens a pull request:

```text
[Auto-Rollback Bot] Disabled flag: new-checkout-flow

Reason: HighErrorRate alert fired at 07:15:28Z.
Flag was enabled 3 minutes prior. Error rate was 35%.
Automatic rollback performed. Error rate recovered to 2%.

See remediation log: http://localhost:5001/api/remediation-log
```

This creates a **complete audit trail in Git** — who enabled the flag, when, why it was rolled back, and what the effect was.

---

## Validation Checklist

- [ ] Listed all flags via `GET /flags`.
- [ ] Enabled `new-checkout-flow` at 10% rollout.
- [ ] Disabled a flag manually with a reason.
- [ ] Triggered the error spike drill.
- [ ] Auto-rollback disabled `new-checkout-flow` within 90 seconds of the alert firing.
- [ ] Verified flag state shows `disabled_at` and `disabled_reason` after rollback.
- [ ] Emergency rollback (`POST /flags/rollback`) disabled all active flags.
