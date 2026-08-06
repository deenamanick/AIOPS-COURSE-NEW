"""Instrumented service with drill endpoints for Module 9 capacity planning labs."""

import time
import random
import threading
import json
from flask import Flask, Response, request, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from datetime import datetime, timezone

app = Flask(__name__)

# Simulated metrics
SIM_DISK = Gauge("sim_disk_usage_pct", "Simulated disk usage percent")
SIM_CPU = Gauge("sim_cpu_usage_pct", "Simulated CPU usage percent")
SIM_MEM = Gauge("sim_memory_usage_pct", "Simulated memory usage percent")
SIM_ERR = Gauge("sim_error_rate_pct", "Simulated error rate percent")

# State
_state = {
    "disk": 20.0,
    "cpu": 25.0,
    "memory": 42.0,
    "error_rate": 0.5,
    "disk_growth_active": False,
    "disk_growth_rate": 0.0,  # % per simulated hour
    "sim_start_time": None,
    "alerts": [],
}

# Predictive alert scheduler
_predictive_alerts = []


def _update_metrics():
    """Background thread that updates simulated metrics every 10 seconds."""
    while True:
        # Add noise to CPU and memory
        _state["cpu"] = max(5, min(95, _state["cpu"] + random.uniform(-3, 3)))
        _state["memory"] = max(20, min(90, _state["memory"] + random.uniform(-1, 1)))
        _state["error_rate"] = max(0, min(20, _state["error_rate"] + random.uniform(-0.3, 0.3)))

        # Disk growth simulation (accelerated: 10s real = 1 simulated hour)
        if _state["disk_growth_active"]:
            _state["disk"] += _state["disk_growth_rate"]
            _state["disk"] = min(100.0, _state["disk"])

            if _state["disk"] >= 100.0:
                actual_time = datetime.now(timezone.utc).isoformat()
                print(f"[DRILL] Disk simulation reached 100% at {actual_time}", flush=True)
                if _state.get("predicted_exhaustion"):
                    print(f"[DRILL] Predicted: {_state['predicted_exhaustion']} | "
                          f"Actual: {actual_time}", flush=True)
                _state["disk_growth_active"] = False

        # Update Prometheus gauges
        SIM_DISK.set(round(_state["disk"], 1))
        SIM_CPU.set(round(_state["cpu"], 1))
        SIM_MEM.set(round(_state["memory"], 1))
        SIM_ERR.set(round(_state["error_rate"], 2))

        # Check predictive alerts
        now = time.time()
        for alert in _predictive_alerts:
            if not alert["fired"] and now >= alert["fire_at"]:
                alert["fired"] = True
                print(f"\n[PREDICTIVE-ALERT] 🚨 FIRING: Disk predicted to exhaust at "
                      f"{alert['predicted_exhaustion']}", flush=True)
                print(f"[PREDICTIVE-ALERT]    Current: {_state['disk']:.1f}% | "
                      f"Rate: +{_state['disk_growth_rate']:.1f}%/hr | "
                      f"ETA: {alert['eta_display']}", flush=True)
                print(f"[PREDICTIVE-ALERT]    Action: Expand volume or clean WAL files NOW\n",
                      flush=True)

        time.sleep(10)


# Start background updater
threading.Thread(target=_update_metrics, daemon=True).start()


@app.get("/")
def index():
    return jsonify({"service": "module-9-capacity-lab", "status": "ok"})


@app.get("/health")
def health():
    return jsonify({"status": "healthy"})


@app.get("/api/metrics")
def api_metrics():
    return jsonify({
        "disk_usage_pct": round(_state["disk"], 1),
        "cpu_usage_pct": round(_state["cpu"], 1),
        "memory_usage_pct": round(_state["memory"], 1),
        "error_rate_pct": round(_state["error_rate"], 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/risk")
def api_risk():
    weights = {"cpu": 0.20, "memory": 0.20, "disk": 0.30, "error_rate": 0.30}
    values = {
        "cpu": max(0, min(100, _state["cpu"])),
        "memory": max(0, min(100, _state["memory"])),
        "disk": max(0, min(100, _state["disk"])),
        "error_rate": max(0, min(100, _state["error_rate"])),
    }
    score = sum(values[k] * weights[k] for k in weights)
    score = round(score, 1)

    if score < 40:
        severity, color = "Low", "Green"
    elif score < 71:
        severity, color = "Medium", "Yellow"
    else:
        severity, color = "High", "Red"

    breakdown = {k: round(values[k] * weights[k], 1) for k in weights}

    return jsonify({
        "score": score,
        "severity": severity,
        "color": color,
        "breakdown": breakdown,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# --- Drill Endpoints ---

@app.post("/drill/disk-growth")
def drill_disk_growth():
    """Start a disk growth simulation. Growth rate: ~10%/simulated-hour.
    At accelerated clock (10s real = 1 sim hour), disk fills in ~8 real minutes."""
    _state["disk_growth_active"] = True
    _state["disk_growth_rate"] = 10.0 + random.uniform(-0.5, 0.5)
    _state["sim_start_time"] = time.time()
    _state["disk"] = 20.0 + random.uniform(-2, 2)

    return jsonify({
        "drill": "disk-growth",
        "active": True,
        "start_disk_pct": round(_state["disk"], 1),
        "growth_rate_per_hour": round(_state["disk_growth_rate"], 1),
        "estimated_hours_to_full": round((100 - _state["disk"]) / _state["disk_growth_rate"], 1),
        "note": "Accelerated clock: 10 seconds real = 1 simulated hour",
    })


@app.post("/drill/set-alert")
def drill_set_alert():
    """Set a predictive alert. Body: {predicted_exhaustion: ISO timestamp, lead_hours: int}"""
    body = request.get_json(force=True)
    predicted = body.get("predicted_exhaustion", "")
    lead_hours = body.get("lead_hours", 2)

    # In accelerated mode: 1 simulated hour = 10 real seconds
    lead_real_seconds = lead_hours * 10
    fire_at = time.time() + max(0, (
        (100 - _state["disk"]) / max(_state["disk_growth_rate"], 0.1) - lead_hours
    ) * 10)

    eta_hours = (100 - _state["disk"]) / max(_state["disk_growth_rate"], 0.1)

    alert = {
        "metric": "disk",
        "predicted_exhaustion": predicted,
        "lead_hours": lead_hours,
        "fire_at": fire_at,
        "fired": False,
        "eta_display": f"{eta_hours - lead_hours:.1f}h remaining at alert time",
    }
    _predictive_alerts.append(alert)
    _state["predicted_exhaustion"] = predicted

    print(f"[ALERT SCHEDULER] Predictive alert set:", flush=True)
    print(f"  Metric:            disk", flush=True)
    print(f"  Predicted failure:  {predicted}", flush=True)
    print(f"  Lead time:         {lead_hours} hours", flush=True)
    print(f"  Status:            ARMED ✅\n", flush=True)

    return jsonify({"status": "armed", "alert": alert})


@app.post("/drill/reset")
def drill_reset():
    _state["disk"] = 20.0
    _state["cpu"] = 25.0
    _state["memory"] = 42.0
    _state["error_rate"] = 0.5
    _state["disk_growth_active"] = False
    _state["disk_growth_rate"] = 0.0
    _state["sim_start_time"] = None
    _predictive_alerts.clear()
    return jsonify({"drill": "reset", "active": False})


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
