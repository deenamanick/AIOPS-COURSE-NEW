"""Instrumented service with webhook receiver, feature flags, and drill endpoints for Module 10."""

import time
import random
import threading
import subprocess
import json
from flask import Flask, Response, request, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from datetime import datetime, timezone
from collections import deque

app = Flask(__name__)

# ── Prometheus gauges ──────────────────────────────────────────────────────────
SIM_DISK = Gauge("sim_disk_usage_pct", "Simulated disk usage percent")
SIM_CPU = Gauge("sim_cpu_usage_pct", "Simulated CPU usage percent")
SIM_MEM = Gauge("sim_memory_usage_pct", "Simulated memory usage percent")
SIM_ERR = Gauge("sim_error_rate_pct", "Simulated error rate percent")
SIM_REPLICAS = Gauge("sim_healthy_replicas", "Number of healthy app replicas")

# ── Shared state ───────────────────────────────────────────────────────────────
_state = {
    "disk": 20.0,
    "cpu": 25.0,
    "memory": 42.0,
    "error_rate": 0.5,
    "replicas": 1,
    "nginx_up": True,
    "disk_spike_active": False,
    "cpu_spike_active": False,
    "error_spike_active": False,
}

# ── Feature flags ──────────────────────────────────────────────────────────────
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
        "rollout_pct": 20,
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

# ── Remediation log ────────────────────────────────────────────────────────────
REMEDIATION_LOG = []

# ── Deduplication & rate limiting ─────────────────────────────────────────────
_seen_group_keys: set = set()
_remediation_times: dict = {}
_playbook_locks = {
    "clear-logs.yml": threading.Lock(),
    "restart-service.yml": threading.Lock(),
    "scale-up.yml": threading.Lock(),
}

# ── Playbook routing ───────────────────────────────────────────────────────────
PLAYBOOK_MAP = {
    "DiskAlmostFull": "clear-logs.yml",
    "NginxDown": "restart-service.yml",
    "HighCPULoad": "scale-up.yml",
    "HighErrorRate": None,  # Handled via feature flag rollback
}


# ── Background metric updater ──────────────────────────────────────────────────
def _update_metrics():
    while True:
        _state["cpu"] = max(5, min(95, _state["cpu"] + random.uniform(-2, 2)))
        _state["memory"] = max(20, min(90, _state["memory"] + random.uniform(-1, 1)))

        if _state["error_spike_active"]:
            _state["error_rate"] = min(40, _state["error_rate"] + random.uniform(0, 1))
        else:
            _state["error_rate"] = max(0, min(5, _state["error_rate"] + random.uniform(-0.2, 0.2)))

        if _state["disk_spike_active"]:
            _state["disk"] = min(95, _state["disk"] + 0.5)

        if _state["cpu_spike_active"]:
            _state["cpu"] = min(95, _state["cpu"] + random.uniform(0, 2))

        SIM_DISK.set(round(_state["disk"], 1))
        SIM_CPU.set(round(_state["cpu"], 1))
        SIM_MEM.set(round(_state["memory"], 1))
        SIM_ERR.set(round(_state["error_rate"], 2))
        SIM_REPLICAS.set(_state["replicas"])

        time.sleep(10)


threading.Thread(target=_update_metrics, daemon=True).start()


# ── Core endpoints ─────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return jsonify({"service": "module-10-remediation-lab", "status": "ok"})


@app.get("/health")
def health():
    return jsonify({"status": "healthy" if _state["nginx_up"] else "degraded"})


@app.get("/api/metrics")
def api_metrics():
    return jsonify({
        "disk_usage_pct": round(_state["disk"], 1),
        "cpu_usage_pct": round(_state["cpu"], 1),
        "memory_usage_pct": round(_state["memory"], 1),
        "error_rate_pct": round(_state["error_rate"], 2),
        "replicas": _state["replicas"],
        "nginx_up": _state["nginx_up"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/status")
def api_status():
    db_ok = random.random() > 0.05
    return jsonify({
        "status": "healthy" if db_ok else "degraded",
        "db_connection": "ok" if db_ok else "circuit-open",
        "message": "All systems operational" if db_ok else "Database unreachable. Serving cached data.",
        "cache_age_sec": 0 if db_ok else random.randint(10, 120),
    })


@app.get("/metrics")
def prometheus_metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# ── Webhook receiver ───────────────────────────────────────────────────────────
@app.post("/webhook")
def webhook():
    """Receive Alertmanager webhook and trigger Ansible playbook or flag rollback."""
    payload = request.get_json(force=True)
    group_key = payload.get("groupKey", "")
    alerts = payload.get("alerts", [])

    for alert in alerts:
        name = alert.get("labels", {}).get("alertname", "")
        status = alert.get("status", "")

        if status == "resolved":
            _log("RESOLVED", name, playbook=None, outcome="alert-cleared")
            _seen_group_keys.discard(group_key)
            continue

        if status != "firing":
            continue

        # Deduplicate
        key = f"{group_key}:{name}"
        if key in _seen_group_keys:
            _log("SKIPPED", name, playbook=None, outcome="duplicate")
            continue
        _seen_group_keys.add(key)

        # Route
        if name == "HighErrorRate":
            threading.Thread(
                target=_auto_rollback_flags, args=(name,), daemon=True
            ).start()
            continue

        playbook = PLAYBOOK_MAP.get(name)
        if not playbook:
            _log("SKIPPED", name, playbook=None, outcome="no-playbook-mapped")
            continue

        # Rate limit check
        times = _remediation_times.setdefault(playbook, deque())
        now = time.time()
        while times and times[0] < now - 600:
            times.popleft()
        if len(times) >= 3:
            _log("SKIPPED", name, playbook=playbook, outcome="rate-limit-hit")
            continue
        times.append(now)

        threading.Thread(
            target=_run_remediation, args=(name, playbook), daemon=True
        ).start()

    return jsonify({"status": "accepted"}), 202


def _run_remediation(alert_name: str, playbook: str):
    lock = _playbook_locks.get(playbook)
    if lock and not lock.acquire(blocking=False):
        _log("SKIPPED", alert_name, playbook=playbook, outcome="already-running")
        return
    try:
        start = time.time()
        _log("STARTED", alert_name, playbook=playbook, outcome="running")

        result = subprocess.run(
            ["ansible-playbook", "-i", "playbooks/inventory.ini",
             f"playbooks/{playbook}", "--connection=local"],
            capture_output=True, text=True, timeout=120
        )

        if result.returncode != 0:
            _log("FAILED", alert_name, playbook=playbook,
                 outcome="playbook-error",
                 detail=result.stderr[-500:],
                 duration=time.time() - start)
            return

        # Simulate remediation effect for lab
        _apply_simulated_fix(alert_name)

        ok = _verify(alert_name)
        outcome = "metric-recovered" if ok else "verify-failed"
        event = "SUCCESS" if ok else "ROLLED_BACK"
        _log(event, alert_name, playbook=playbook,
             outcome=outcome, duration=time.time() - start)
    except subprocess.TimeoutExpired:
        _log("TIMEOUT", alert_name, playbook=playbook,
             outcome="playbook-timeout",
             duration=120)
    finally:
        if lock:
            lock.release()


def _apply_simulated_fix(alert_name: str):
    """Simulate the metric recovery that the playbook would cause."""
    if alert_name == "DiskAlmostFull":
        _state["disk"] = max(20, _state["disk"] - 30)
        _state["disk_spike_active"] = False
    elif alert_name == "NginxDown":
        _state["nginx_up"] = True
    elif alert_name == "HighCPULoad":
        _state["replicas"] = min(5, _state["replicas"] + 1)
        _state["cpu"] = max(20, _state["cpu"] - 25)
        _state["cpu_spike_active"] = False


def _verify(alert_name: str) -> bool:
    """Poll the metric for up to 60 seconds to confirm recovery."""
    deadline = time.time() + 60
    while time.time() < deadline:
        if alert_name == "DiskAlmostFull" and _state["disk"] < 80:
            return True
        if alert_name == "NginxDown" and _state["nginx_up"]:
            return True
        if alert_name == "HighCPULoad" and _state["cpu"] < 75:
            return True
        time.sleep(5)
    return False


def _auto_rollback_flags(alert_name: str):
    """Disable recently-enabled flags when a HighErrorRate alert fires."""
    start = time.time()
    _log("STARTED", alert_name, playbook=None, outcome="flag-rollback-initiated")
    disabled = []
    for name, flag in _flags.items():
        if flag.get("enabled"):
            flag.update({
                "enabled": False,
                "rollout_pct": 0,
                "disabled_at": datetime.now(timezone.utc).isoformat(),
                "disabled_reason": f"Auto-rollback: {alert_name} anomaly detected.",
            })
            disabled.append(name)

    # Simulate error rate recovery after flags disabled
    _state["error_spike_active"] = False
    _state["error_rate"] = max(0, _state["error_rate"] - 25)

    time.sleep(15)
    ok = _state["error_rate"] < 10
    _log("SUCCESS" if ok else "ROLLED_BACK", alert_name, playbook=None,
         outcome="flags-disabled" if ok else "verify-failed",
         detail=f"Disabled flags: {disabled}",
         duration=time.time() - start)


def _log(event, alert_name, playbook, outcome, detail="", duration=0):
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


# ── Remediation log endpoint ───────────────────────────────────────────────────
@app.get("/api/remediation-log")
def remediation_log():
    return jsonify(REMEDIATION_LOG)


# ── Feature flag endpoints ─────────────────────────────────────────────────────
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
        "created_at": datetime.now(timezone.utc).isoformat(),
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
    _flags[name].update({
        "enabled": False,
        "rollout_pct": 0,
        "disabled_at": datetime.now(timezone.utc).isoformat(),
        "disabled_reason": reason,
    })
    return jsonify({"status": "disabled", "flag": name, "reason": reason})


@app.post("/flags/rollback")
def rollback_all():
    """Emergency: disable all currently-enabled flags."""
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


# ── Chaos / Drill endpoints ────────────────────────────────────────────────────
@app.post("/drill/disk-spike")
def drill_disk_spike():
    _state["disk"] = 90.0
    _state["disk_spike_active"] = True
    return jsonify({"drill": "disk-spike", "disk_pct": _state["disk"],
                    "note": "Disk set to 90%. DiskAlmostFull will fire after 2 minutes."})


@app.post("/drill/nginx-down")
def drill_nginx_down():
    _state["nginx_up"] = False
    return jsonify({"drill": "nginx-down", "nginx_up": False,
                    "note": "Nginx marked as down. NginxDown will fire after 30 seconds."})


@app.post("/drill/cpu-spike")
def drill_cpu_spike():
    _state["cpu"] = 85.0
    _state["cpu_spike_active"] = True
    return jsonify({"drill": "cpu-spike", "cpu_pct": _state["cpu"],
                    "note": "CPU set to 85%. HighCPULoad will fire after 5 minutes."})


@app.post("/drill/error-spike")
def drill_error_spike():
    _state["error_rate"] = 35.0
    _state["error_spike_active"] = True
    return jsonify({"drill": "error-spike", "error_rate_pct": _state["error_rate"],
                    "note": "Error rate set to 35%. HighErrorRate will fire after 1 minute."})


@app.post("/drill/reset")
def drill_reset():
    _state.update({
        "disk": 20.0, "cpu": 25.0, "memory": 42.0, "error_rate": 0.5,
        "replicas": 1, "nginx_up": True,
        "disk_spike_active": False, "cpu_spike_active": False, "error_spike_active": False,
    })
    return jsonify({"drill": "reset", "state": "nominal"})


@app.get("/chaos/status")
def chaos_status():
    return jsonify({
        "disk_spike_active": _state["disk_spike_active"],
        "cpu_spike_active": _state["cpu_spike_active"],
        "error_spike_active": _state["error_spike_active"],
        "nginx_up": _state["nginx_up"],
        "replicas": _state["replicas"],
        "disk_pct": round(_state["disk"], 1),
        "cpu_pct": round(_state["cpu"], 1),
        "error_rate_pct": round(_state["error_rate"], 2),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
