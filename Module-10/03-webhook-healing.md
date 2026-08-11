# 03 — Webhook-Triggered Healing

In the previous lesson, you ran Ansible playbooks manually. That is useful for understanding playbooks, but it defeats the purpose of auto-remediation. In this lesson, you will configure Alertmanager to send an HTTP webhook to a Python Flask receiver, and the receiver will automatically select and execute the correct Ansible playbook. The full flow: **disk fills → alert fires → webhook triggers → Ansible cleans logs → alert resolves**.

---

## The Full End-to-End Flow

```text
1. Disk usage climbs above 85%
2. Prometheus scrapes the metric every 15 seconds
3. Alertmanager evaluates the DiskAlmostFull rule
4. After 2 minutes in firing state, Alertmanager sends a POST to the webhook receiver
5. Flask receiver validates the payload and identifies the alert
6. Flask spawns an Ansible subprocess: clear-logs.yml
7. Ansible deletes old logs, disk drops below 80%
8. Prometheus detects the metric recovery
9. Alertmanager sends a "resolved" webhook — receiver logs the resolution
```

---

## Step 1: Alertmanager Configuration

Create or update `alertmanager.yml` to add a webhook receiver:

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ["alertname", "severity"]
  group_wait: 30s
  group_interval: 2m
  repeat_interval: 4h
  receiver: "default"
  routes:
    - match:
        alertname: DiskAlmostFull
      receiver: "ansible-webhook"
      continue: false

    - match:
        alertname: NginxDown
      receiver: "ansible-webhook"
      continue: false

    - match:
        alertname: HighCPULoad
      receiver: "ansible-webhook"
      continue: false

receivers:
  - name: "default"
    # no-op receiver for non-automatable alerts

  - name: "ansible-webhook"
    webhook_configs:
      - url: "http://localhost:5001/webhook"
        send_resolved: true
        http_config:
          follow_redirects: true
        max_alerts: 10
```

The `send_resolved: true` flag is important — it ensures the webhook receives a "resolved" event when the alert clears, so the receiver can log the recovery and stop any retry loops.

---

## Step 2: Prometheus Alert Rules

Create `rules/remediation.yml`:

```yaml
# rules/remediation.yml
groups:
  - name: auto-remediation
    interval: 15s
    rules:
      - alert: DiskAlmostFull
        expr: sim_disk_usage_pct > 85
        for: 2m
        labels:
          severity: warning
          auto_remediate: "true"
        annotations:
          summary: "Disk usage above 85% on {{ $labels.instance }}"
          description: "Disk is at {{ $value | printf \"%.1f\" }}%. Triggering log cleanup."

      - alert: NginxDown
        expr: up{job="nginx"} == 0
        for: 30s
        labels:
          severity: critical
          auto_remediate: "true"
        annotations:
          summary: "Nginx is down on {{ $labels.instance }}"
          description: "Nginx exporter is unreachable. Triggering service restart."

      - alert: HighCPULoad
        expr: sim_cpu_usage_pct > 80
        for: 5m
        labels:
          severity: warning
          auto_remediate: "true"
        annotations:
          summary: "CPU load above 80% for 5 minutes on {{ $labels.instance }}"
          description: "CPU at {{ $value | printf \"%.1f\" }}%. Triggering scale-up."
```

---

## Step 3: The Flask Webhook Receiver

The webhook receiver is the core of the auto-remediation system. It lives in `lab/app/app.py` alongside the metrics simulator:

```python
# Core webhook handler (from lab/app/app.py)
import subprocess, time, threading
from flask import Flask, request, jsonify
from datetime import datetime, timezone

PLAYBOOK_MAP = {
    "DiskAlmostFull": "clear-logs.yml",
    "NginxDown": "restart-service.yml",
    "HighCPULoad": "scale-up.yml",
}

REMEDIATION_LOG = []


@app.post("/webhook")
def webhook():
    """Receive Alertmanager webhook and trigger the appropriate Ansible playbook."""
    payload = request.get_json(force=True)
    alerts = payload.get("alerts", [])

    for alert in alerts:
        name = alert.get("labels", {}).get("alertname", "")
        status = alert.get("status", "")

        if status == "resolved":
            _log("RESOLVED", name, playbook=None, outcome="alert-cleared")
            continue

        if status != "firing":
            continue

        playbook = PLAYBOOK_MAP.get(name)
        if not playbook:
            _log("SKIPPED", name, playbook=None, outcome="no-playbook-mapped")
            continue

        # Launch remediation in background thread so webhook returns immediately
        threading.Thread(
            target=_run_remediation,
            args=(name, playbook, alert),
            daemon=True
        ).start()

    return jsonify({"status": "accepted"}), 202


def _run_remediation(alert_name: str, playbook: str, alert: dict):
    """Execute Ansible playbook and verify the outcome."""
    start = time.time()
    _log("STARTED", alert_name, playbook=playbook, outcome="running")

    try:
        result = subprocess.run(
            ["ansible-playbook", "-i", "playbooks/inventory.ini",
             f"playbooks/{playbook}", "--connection=local"],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            _log("FAILED", alert_name, playbook=playbook,
                 outcome="playbook-error", detail=result.stderr[-500:],
                 duration=time.time() - start)
            return

        # Verify the fix
        ok = _verify(alert_name)
        if ok:
            _log("SUCCESS", alert_name, playbook=playbook,
                 outcome="metric-recovered", duration=time.time() - start)
        else:
            _log("ROLLED_BACK", alert_name, playbook=playbook,
                 outcome="verify-failed", duration=time.time() - start)

    except subprocess.TimeoutExpired:
        _log("TIMEOUT", alert_name, playbook=playbook,
             outcome="playbook-timeout", duration=time.time() - start)


def _verify(alert_name: str) -> bool:
    """Poll the metric for up to 60 seconds to confirm recovery."""
    deadline = time.time() + 60
    while time.time() < deadline:
        if alert_name == "DiskAlmostFull" and _state["disk"] < 80:
            return True
        if alert_name == "NginxDown" and _nginx_running():
            return True
        if alert_name == "HighCPULoad" and _state["cpu"] < 75:
            return True
        time.sleep(5)
    return False


def _log(event: str, alert_name: str, playbook, outcome: str,
         detail: str = "", duration: float = 0):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "alert": alert_name,
        "playbook": playbook,
        "outcome": outcome,
        "detail": detail,
        "duration_sec": round(duration, 1),
    }
    REMEDIATION_LOG.append(entry)
    print(f"[REMEDIATION] {event} | {alert_name} | {outcome}", flush=True)


@app.get("/api/remediation-log")
def remediation_log():
    return jsonify(REMEDIATION_LOG)
```

---

## Step 4: Run the End-to-End Test

### Start the lab

```bash
cd Module-10/lab
docker compose up -d --build
```

### Trigger the DiskAlmostFull alert

```bash
curl -X POST http://localhost:5001/drill/disk-spike
```

This sets the simulated disk to 90%. Prometheus will detect this within 15 seconds. After 2 minutes in firing state, Alertmanager fires the webhook.

### Watch the remediation log

```bash
watch -n 2 "curl -s http://localhost:5001/api/remediation-log | python3 -m json.tool"
```

Expected progression:

```json
[
  {
    "timestamp": "2026-08-11T06:10:00Z",
    "event": "STARTED",
    "alert": "DiskAlmostFull",
    "playbook": "clear-logs.yml",
    "outcome": "running",
    "duration_sec": 0
  },
  {
    "timestamp": "2026-08-11T06:10:28Z",
    "event": "SUCCESS",
    "alert": "DiskAlmostFull",
    "playbook": "clear-logs.yml",
    "outcome": "metric-recovered",
    "detail": "",
    "duration_sec": 28.3
  },
  {
    "timestamp": "2026-08-11T06:12:15Z",
    "event": "RESOLVED",
    "alert": "DiskAlmostFull",
    "playbook": null,
    "outcome": "alert-cleared",
    "duration_sec": 0
  }
]
```

### Manually send a test webhook (without waiting for Prometheus)

```bash
curl -X POST http://localhost:5001/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "version": "4",
    "groupKey": "{}:{alertname=\"DiskAlmostFull\"}",
    "status": "firing",
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "DiskAlmostFull",
          "severity": "warning",
          "instance": "localhost:5001"
        },
        "annotations": {
          "summary": "Disk usage above 85%"
        }
      }
    ]
  }'
```

---

## Anatomy of the Alertmanager Webhook Payload

Understanding the payload structure is essential for writing a robust receiver:

| Field | Description |
|---|---|
| `version` | Alertmanager payload version (always "4" currently) |
| `groupKey` | Unique key for this alert group — use to deduplicate |
| `status` | `"firing"` or `"resolved"` |
| `alerts[]` | Array of alerts in this group (may be more than 1) |
| `alerts[].labels.alertname` | The rule name from `rules/*.yml` |
| `alerts[].labels.severity` | Label from the rule |
| `alerts[].annotations.summary` | Human-readable alert description |

Always iterate over `alerts[]`—a single webhook call can contain multiple firing alerts from the same group.

---

## Validation Checklist

- [ ] Alertmanager config routes `DiskAlmostFull`, `NginxDown`, and `HighCPULoad` to the webhook receiver.
- [ ] Webhook receiver correctly identifies and skips resolved alerts.
- [ ] Unknown alertnames are logged as "SKIPPED" — no playbook runs.
- [ ] `DiskAlmostFull` drill triggers `clear-logs.yml` automatically.
- [ ] Remediation log shows: STARTED → SUCCESS (or ROLLED_BACK if verify fails).
- [ ] Manual webhook payload test returns HTTP 202 and triggers the playbook.
