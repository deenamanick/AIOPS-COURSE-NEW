"""Markov chain predictive analysis lab service — Module 13.

Simulates a system cycling through Healthy → Degraded → Critical → Failed
states. Provides drill endpoints to inject load and observe the Markov
model predict and prevent failure.
"""

import time
import random
import threading
import json
import numpy as np
from datetime import datetime, timezone
from flask import Flask, Response, request, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, Enum, generate_latest

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Prometheus gauges
# ---------------------------------------------------------------------------
SIM_CPU = Gauge("sim_cpu_usage_pct", "Simulated CPU usage percent")
SIM_MEM = Gauge("sim_memory_usage_pct", "Simulated memory usage percent")
SIM_DISK = Gauge("sim_disk_usage_pct", "Simulated disk usage percent")
SIM_ERR = Gauge("sim_error_rate_pct", "Simulated error rate percent")
SIM_P_FAILED = Gauge("markov_p_failed", "Predicted probability of reaching Failed state")
SIM_STATE = Enum("markov_current_state", "Current operational state",
                 states=["Healthy", "Degraded", "Critical", "Failed"])

# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------
STATES = ["Healthy", "Degraded", "Critical", "Failed"]

_state = {
    "cpu": 28.0,
    "mem": 42.0,
    "disk": 35.0,
    "error_rate": 0.02,
    "current_state": "Healthy",
    "drill_active": False,
    "drill_phase": 0,          # 0=none, 1=degrading, 2=critical, 3=recovering
    "drill_tick": 0,
    "drill_log": [],
    "p_failed": 0.0,
    "remediation_applied": False,
    "start_time": time.time(),
}

# Default transition matrix (can be overridden via API)
DEFAULT_MATRIX = np.array([
    [0.85, 0.12, 0.02, 0.01],   # Healthy
    [0.15, 0.60, 0.20, 0.05],   # Degraded
    [0.05, 0.10, 0.55, 0.30],   # Critical
    [0.10, 0.05, 0.05, 0.80],   # Failed
])

_transition_matrix = DEFAULT_MATRIX.copy()


# ---------------------------------------------------------------------------
# State mapping
# ---------------------------------------------------------------------------
def _map_state(cpu, mem, disk, error_rate):
    """Map continuous metrics to a discrete operational state."""
    if error_rate > 0.50:
        return "Failed"
    if cpu > 80 or mem > 80 or disk > 90:
        return "Critical"
    if cpu > 60 or mem > 60 or disk > 75:
        return "Degraded"
    return "Healthy"


def _forecast_p_failed(current_state, steps=6):
    """Compute P(Failed) in N steps from current state."""
    vec = np.zeros(len(STATES))
    vec[STATES.index(current_state)] = 1.0
    for _ in range(steps):
        vec = vec @ _transition_matrix
    return float(vec[STATES.index("Failed")])


# ---------------------------------------------------------------------------
# Background thread — updates metrics every 10 seconds
# ---------------------------------------------------------------------------
def _update_metrics():
    """Background thread simulating system behavior."""
    while True:
        prev_state = _state["current_state"]

        if _state["drill_active"]:
            _state["drill_tick"] += 1
            tick = _state["drill_tick"]

            if _state["remediation_applied"]:
                # Recovery phase: bring metrics back down
                _state["cpu"] = max(25, _state["cpu"] - 12 + random.uniform(-2, 2))
                _state["mem"] = max(40, _state["mem"] - 8 + random.uniform(-1, 1))
                _state["error_rate"] = max(0.01, _state["error_rate"] - 0.08)
                _state["drill_phase"] = 3
            elif tick <= 6:
                # Phase 1: Degradation (ticks 1-6 → ~60 seconds)
                _state["cpu"] += 7 + random.uniform(-1, 2)
                _state["mem"] += 4 + random.uniform(-1, 1)
                _state["error_rate"] += 0.02 + random.uniform(0, 0.01)
                _state["drill_phase"] = 1
            elif tick <= 12:
                # Phase 2: Critical (ticks 7-12 → ~120 seconds)
                _state["cpu"] += 3 + random.uniform(0, 2)
                _state["mem"] += 2 + random.uniform(0, 1)
                _state["error_rate"] += 0.05 + random.uniform(0, 0.03)
                _state["drill_phase"] = 2
            else:
                # Phase 3: would fail without remediation
                _state["error_rate"] += 0.1
                _state["drill_phase"] = 2

            # Clamp values
            _state["cpu"] = min(98, max(5, _state["cpu"]))
            _state["mem"] = min(95, max(20, _state["mem"]))
            _state["error_rate"] = min(0.95, max(0, _state["error_rate"]))

        else:
            # Normal operation: gentle noise
            _state["cpu"] = max(15, min(55, _state["cpu"] + random.uniform(-3, 3)))
            _state["mem"] = max(35, min(55, _state["mem"] + random.uniform(-1, 1)))
            _state["error_rate"] = max(0.01, min(0.05,
                                       _state["error_rate"] + random.uniform(-0.005, 0.005)))

        # Map to state
        new_state = _map_state(_state["cpu"], _state["mem"], _state["disk"],
                               _state["error_rate"])
        _state["current_state"] = new_state

        # Compute forecast
        _state["p_failed"] = _forecast_p_failed(new_state, steps=6)

        # Log state transitions
        if new_state != prev_state:
            ts = datetime.now(timezone.utc).isoformat()
            event = {
                "time": ts,
                "event": "state_change",
                "from": prev_state,
                "to": new_state,
            }
            _state["drill_log"].append(event)
            print(f"[MARKOV] State transition: {prev_state} → {new_state} "
                  f"(cpu={_state['cpu']:.1f}%)", flush=True)

        # Check if remediation is needed during drill
        if (_state["drill_active"] and not _state["remediation_applied"]
                and _state["p_failed"] >= 0.60):
            ts = datetime.now(timezone.utc).isoformat()
            print(f"\n[MARKOV] ⚠️ Forecast: P(Failed) = {_state['p_failed']:.1%} "
                  f"at step 6 — THRESHOLD EXCEEDED", flush=True)
            print(f"[MARKOV] 📡 Triggering auto-remediation...", flush=True)
            _state["drill_log"].append({
                "time": ts, "event": "forecast_alert",
                "p_failed": round(_state["p_failed"], 3), "steps": 6,
            })
            # Simulate remediation
            _state["remediation_applied"] = True
            _state["drill_log"].append({
                "time": ts, "event": "remediation_applied", "action": "scale-up",
            })
            print(f"[MARKOV] 🔧 Remediation applied — scaling up\n", flush=True)

        # Check drill completion (recovered after remediation)
        if (_state["drill_active"] and _state["remediation_applied"]
                and new_state == "Healthy"):
            ts = datetime.now(timezone.utc).isoformat()
            _state["drill_log"].append({
                "time": ts, "event": "drill_completed", "outcome": "prevented",
            })
            _state["drill_active"] = False
            print(f"[MARKOV] ✅ System restored to Healthy state\n", flush=True)

        # Update Prometheus gauges
        SIM_CPU.set(round(_state["cpu"], 1))
        SIM_MEM.set(round(_state["mem"], 1))
        SIM_DISK.set(round(_state["disk"], 1))
        SIM_ERR.set(round(_state["error_rate"], 3))
        SIM_P_FAILED.set(round(_state["p_failed"], 4))
        SIM_STATE.state(new_state)

        time.sleep(10)


# Start background updater
threading.Thread(target=_update_metrics, daemon=True).start()


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    return jsonify({"service": "module-13-markov-lab", "status": "ok"})


@app.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "current_state": _state["current_state"],
        "uptime_seconds": int(time.time() - _state["start_time"]),
    })


@app.get("/api/state")
def api_state():
    return jsonify({
        "state": _state["current_state"],
        "cpu": round(_state["cpu"], 1),
        "mem": round(_state["mem"], 1),
        "disk": round(_state["disk"], 1),
        "error_rate": round(_state["error_rate"], 3),
        "p_failed": round(_state["p_failed"], 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/matrix")
def api_matrix():
    matrix_dict = {}
    for i, from_state in enumerate(STATES):
        matrix_dict[from_state] = {
            to_state: round(float(_transition_matrix[i][j]), 4)
            for j, to_state in enumerate(STATES)
        }
    return jsonify({"states": STATES, "matrix": matrix_dict})


@app.post("/api/matrix")
def update_matrix():
    """Upload a custom transition matrix (4×4 JSON array)."""
    body = request.get_json(force=True)
    try:
        mat = np.array(body["matrix"], dtype=float)
        assert mat.shape == (4, 4), "Matrix must be 4×4"
        for i in range(4):
            row_sum = mat[i].sum()
            assert abs(row_sum - 1.0) < 0.01, f"Row {i} sums to {row_sum}, expected 1.0"
        global _transition_matrix
        _transition_matrix = mat
        return jsonify({"status": "updated", "matrix": mat.tolist()})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.get("/api/forecast")
def api_forecast():
    """Forecast P(Failed) from current state over N steps."""
    steps = request.args.get("steps", 6, type=int)
    state = request.args.get("state", _state["current_state"])
    if state not in STATES:
        return jsonify({"error": f"Unknown state: {state}"}), 400

    vec = np.zeros(len(STATES))
    vec[STATES.index(state)] = 1.0
    results = []
    for step in range(1, steps + 1):
        vec = vec @ _transition_matrix
        results.append({
            "step": step,
            "distribution": {s: round(float(vec[i]), 4) for i, s in enumerate(STATES)},
            "p_failed": round(float(vec[STATES.index("Failed")]), 4),
        })

    return jsonify({
        "start_state": state,
        "steps": steps,
        "threshold": 0.60,
        "forecast": results,
        "final_p_failed": results[-1]["p_failed"],
        "threshold_exceeded": results[-1]["p_failed"] >= 0.60,
    })


# ---------------------------------------------------------------------------
# Drill endpoints
# ---------------------------------------------------------------------------
@app.post("/drill/inject-load")
def drill_inject_load():
    """Start a load injection drill. System will transition through states."""
    _state["drill_active"] = True
    _state["drill_tick"] = 0
    _state["drill_phase"] = 0
    _state["remediation_applied"] = False
    _state["drill_log"] = [{
        "time": datetime.now(timezone.utc).isoformat(),
        "event": "drill_started",
        "state": _state["current_state"],
    }]
    print(f"\n[MARKOV] 🚀 Drill started — injecting load\n", flush=True)
    return jsonify({
        "drill": "inject-load",
        "active": True,
        "phase": "degradation",
        "note": "System will transition Healthy → Degraded → Critical over ~2 minutes (accelerated)",
    })


@app.post("/drill/reset")
def drill_reset():
    """Reset the system to baseline."""
    _state["cpu"] = 28.0
    _state["mem"] = 42.0
    _state["disk"] = 35.0
    _state["error_rate"] = 0.02
    _state["current_state"] = "Healthy"
    _state["drill_active"] = False
    _state["drill_phase"] = 0
    _state["drill_tick"] = 0
    _state["remediation_applied"] = False
    _state["p_failed"] = 0.0
    global _transition_matrix
    _transition_matrix = DEFAULT_MATRIX.copy()
    print(f"[MARKOV] 🔄 Drill reset — system restored to baseline\n", flush=True)
    return jsonify({"drill": "reset", "active": False, "state": "Healthy"})


@app.get("/api/drill-log")
def drill_log():
    """Return the timeline of drill events."""
    return jsonify({"events": _state["drill_log"]})


@app.post("/api/remediate")
def remediate():
    """External remediation trigger (e.g., from Ansible webhook response)."""
    if _state["drill_active"] and not _state["remediation_applied"]:
        _state["remediation_applied"] = True
        ts = datetime.now(timezone.utc).isoformat()
        _state["drill_log"].append({
            "time": ts, "event": "remediation_applied",
            "action": "external-trigger",
        })
        print(f"[MARKOV] 🔧 External remediation received\n", flush=True)
        return jsonify({"status": "remediation_accepted"})
    return jsonify({"status": "no_active_drill_or_already_remediated"})


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
