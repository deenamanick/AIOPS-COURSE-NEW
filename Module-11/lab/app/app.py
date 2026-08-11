"""Module 11 lab app — incident context, anomaly scores, forecast, logs, and drill endpoints."""

import time
import random
import threading
from flask import Flask, Response, request, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from datetime import datetime, timezone

app = Flask(__name__)

# ── Prometheus gauges ──────────────────────────────────────────────────────────
SIM_DISK = Gauge("sim_disk_usage_pct", "Simulated disk usage percent")
SIM_CPU = Gauge("sim_cpu_usage_pct", "Simulated CPU usage percent")
SIM_MEM = Gauge("sim_memory_usage_pct", "Simulated memory usage percent")
SIM_ERR = Gauge("sim_error_rate_pct", "Simulated error rate percent")
SIM_LATENCY = Gauge("sim_latency_p99_ms", "Simulated p99 latency in ms")

# ── Shared state ───────────────────────────────────────────────────────────────
_state = {
    "disk": 20.0,
    "cpu": 25.0,
    "memory": 42.0,
    "error_rate": 0.4,
    "latency_p99": 120.0,
    "wal_growth_active": False,
    "wal_growth_rate": 0.0,
    "inject_time": None,
}

# ── Simulated log ring buffer (last 50 entries) ────────────────────────────────
_LOG_BUFFER: list = []
_LOG_MAX = 50

# ── Correlated alerts ──────────────────────────────────────────────────────────
_ALERT_HISTORY: list = []


def _push_log(level: str, source: str, message: str):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "source": source,
        "message": message,
    }
    _LOG_BUFFER.append(entry)
    if len(_LOG_BUFFER) > _LOG_MAX:
        _LOG_BUFFER.pop(0)


def _push_alert(name: str, severity: str, value: float, unit: str):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alertname": name,
        "severity": severity,
        "value": round(value, 1),
        "unit": unit,
        "status": "firing",
    }
    _ALERT_HISTORY.append(entry)
    if len(_ALERT_HISTORY) > 20:
        _ALERT_HISTORY.pop(0)


# ── Background metric updater ──────────────────────────────────────────────────
def _update_metrics():
    tick = 0
    while True:
        _state["cpu"] = max(5, min(95, _state["cpu"] + random.uniform(-2, 2)))
        _state["memory"] = max(20, min(90, _state["memory"] + random.uniform(-0.5, 0.5)))

        if _state["wal_growth_active"]:
            _state["disk"] = min(100.0, _state["disk"] + _state["wal_growth_rate"])

            # Cascade to application layer once disk > 80%
            if _state["disk"] > 80:
                _state["error_rate"] = min(30, _state["error_rate"] + random.uniform(0.2, 1.0))
                _state["latency_p99"] = min(8000, _state["latency_p99"] + random.uniform(20, 100))

                if tick % 3 == 0:
                    _push_log("ERROR", "db-server-01", "write failed: no space left on device")
                if tick % 5 == 0:
                    _push_log("ERROR", "app-server-01", "db connection timeout after 30s")
                if tick % 7 == 0:
                    _push_log("WARN", "app-server-01",
                              f"slow query: SELECT * FROM events took {random.uniform(8, 20):.1f}s")
            if _state["disk"] > 85 and tick % 4 == 0:
                _push_log("ERROR", "db-server-01", "WAL archive log rotation failed — disk full")
                _push_alert("DiskAlmostFull", "warning", _state["disk"], "%")
            if _state["error_rate"] > 20 and tick % 6 == 0:
                _push_alert("DBConnectionErrors", "critical", _state["error_rate"], "%")
            if _state["latency_p99"] > 2000 and tick % 8 == 0:
                _push_alert("AppSlowResponse", "warning", _state["latency_p99"], "ms")
        else:
            _state["error_rate"] = max(0, min(1, _state["error_rate"] + random.uniform(-0.1, 0.1)))
            _state["latency_p99"] = max(80, min(200, _state["latency_p99"] + random.uniform(-5, 5)))

        SIM_DISK.set(round(_state["disk"], 1))
        SIM_CPU.set(round(_state["cpu"], 1))
        SIM_MEM.set(round(_state["memory"], 1))
        SIM_ERR.set(round(_state["error_rate"], 2))
        SIM_LATENCY.set(round(_state["latency_p99"], 1))

        tick += 1
        time.sleep(10)


threading.Thread(target=_update_metrics, daemon=True).start()

# Seed some baseline logs
for _ in range(5):
    _push_log("INFO", "app-server-01", "request /api/checkout processed in 95ms")
    _push_log("INFO", "db-server-01", "WAL archive rotation complete")


# ── Core endpoints ─────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return jsonify({"service": "module-11-capstone-lab", "status": "ok"})


@app.get("/health")
def health():
    ok = _state["disk"] < 95 and _state["error_rate"] < 25
    return jsonify({"status": "healthy" if ok else "degraded"})


@app.get("/api/metrics")
def api_metrics():
    return jsonify({
        "disk_usage_pct": round(_state["disk"], 1),
        "cpu_usage_pct": round(_state["cpu"], 1),
        "memory_usage_pct": round(_state["memory"], 1),
        "error_rate_pct": round(_state["error_rate"], 2),
        "latency_p99_ms": round(_state["latency_p99"], 1),
        "wal_growth_active": _state["wal_growth_active"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/logs")
def api_logs():
    """Return the last N log lines (default: 20)."""
    n = min(int(request.args.get("n", 20)), _LOG_MAX)
    return jsonify(_LOG_BUFFER[-n:])


@app.get("/api/alerts")
def api_alerts():
    return jsonify(_ALERT_HISTORY)


@app.get("/api/anomaly")
def api_anomaly():
    """Compute simple Z-score-style anomaly scores for each metric."""
    # Simplified scoring: 0=normal, 100=maximally anomalous
    disk_score = min(100, max(0, (_state["disk"] - 60) * 2.5)) if _state["disk"] > 60 else 0
    err_score = min(100, _state["error_rate"] * 4)
    lat_score = min(100, max(0, (_state["latency_p99"] - 200) / 40))
    composite = round(disk_score * 0.5 + err_score * 0.3 + lat_score * 0.2, 1)

    if composite >= 70:
        severity = "CRITICAL"
    elif composite >= 40:
        severity = "HIGH"
    elif composite >= 20:
        severity = "ELEVATED"
    else:
        severity = "NORMAL"

    return jsonify({
        "disk_anomaly_score": round(disk_score, 1),
        "error_rate_anomaly_score": round(err_score, 1),
        "latency_anomaly_score": round(lat_score, 1),
        "composite_score": composite,
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/forecast")
def api_forecast():
    """Return a simple linear forecast for disk."""
    if not _state["wal_growth_active"] or _state["wal_growth_rate"] <= 0:
        return jsonify({"status": "no-growth-active", "message": "Disk is stable."})
    hours_to_full = round((100 - _state["disk"]) / _state["wal_growth_rate"], 1)
    return jsonify({
        "metric": "disk_usage_pct",
        "current_pct": round(_state["disk"], 1),
        "growth_rate_pct_per_hour": round(_state["wal_growth_rate"], 1),
        "hours_to_100_pct": hours_to_full,
        "r2_score": 0.96,
        "alert_message": f"🚨 Disk will exhaust in {hours_to_full:.1f} hours!" if hours_to_full < 3 else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/incident-context")
def api_incident_context():
    """Return all incident data in one call for prompt building."""
    return jsonify({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": "training",
        "metrics": {
            "disk_usage_pct": round(_state["disk"], 1),
            "cpu_usage_pct": round(_state["cpu"], 1),
            "memory_usage_pct": round(_state["memory"], 1),
            "error_rate_pct": round(_state["error_rate"], 2),
            "latency_p99_ms": round(_state["latency_p99"], 1),
        },
        "active_alerts": _ALERT_HISTORY[-10:],
        "recent_logs": _LOG_BUFFER[-20:],
        "anomaly": api_anomaly().get_json(),
        "forecast": api_forecast().get_json(),
    })


@app.get("/api/status")
def api_status():
    ok = _state["disk"] < 95 and _state["error_rate"] < 20
    return jsonify({
        "status": "healthy" if ok else "degraded",
        "db_connection": "ok" if _state["error_rate"] < 10 else "degraded",
        "message": "All systems operational" if ok else "Disk pressure causing DB errors",
    })


@app.get("/metrics")
def prometheus_metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# ── Drill endpoints ────────────────────────────────────────────────────────────
@app.post("/drill/wal-growth")
def drill_wal_growth():
    """Start WAL archive growth simulation."""
    rate = round(random.uniform(9.0, 11.0), 1)
    _state["wal_growth_active"] = True
    _state["wal_growth_rate"] = rate
    _state["disk"] = round(random.uniform(18, 22), 1)
    _state["inject_time"] = datetime.now(timezone.utc).isoformat()
    _push_log("INFO", "drill", f"WAL archive growth drill started at rate {rate}%/hr")
    return jsonify({
        "drill": "wal-growth",
        "active": True,
        "start_disk_pct": round(_state["disk"], 1),
        "growth_rate_pct_per_hour": rate,
        "estimated_hours_to_full": round((100 - _state["disk"]) / rate, 1),
        "note": "Accelerated clock: 10 seconds real = 1 simulated hour",
    })


@app.post("/drill/reset")
def drill_reset():
    _state.update({
        "disk": 20.0, "cpu": 25.0, "memory": 42.0,
        "error_rate": 0.4, "latency_p99": 120.0,
        "wal_growth_active": False, "wal_growth_rate": 0.0, "inject_time": None,
    })
    _ALERT_HISTORY.clear()
    _push_log("INFO", "drill", "All drills reset to baseline.")
    return jsonify({"drill": "reset", "state": "nominal"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
