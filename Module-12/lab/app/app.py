"""Module 12 lab app — security telemetry simulation with insider threat injection."""

import time
import random
import threading
from datetime import datetime, timezone, timedelta
from flask import Flask, Response, request, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

app = Flask(__name__)

# ── Prometheus gauges ──────────────────────────────────────────────────────────
SIM_LOGIN_RATE   = Gauge("sim_login_rate",     "Logins per minute across all users")
SIM_TRANSFER_MB  = Gauge("sim_transfer_mb",    "Data transferred MB in last 5 min")
SIM_FAIL_LOGINS  = Gauge("sim_failed_logins",  "Failed login attempts in last 5 min")
SIM_ANOMALY      = Gauge("sim_anomaly_score",  "Current insider threat anomaly score (0-100)")
SIM_COMPLIANCE   = Gauge("sim_compliance_failures", "Number of failing compliance controls")

# ── State ──────────────────────────────────────────────────────────────────────
_state = {
    "insider_threat_active": False,
    "threat_user": None,
    "threat_type": None,
    "threat_start": None,
}
_USERS = ["alice", "bob", "carol", "dave", "eve"]

# ── Session and event ring buffers ─────────────────────────────────────────────
_SESSIONS: list = []
_EVENTS:   list = []
_MAX      = 500


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rand_user() -> str:
    # bob is slightly more active to make the anomaly more noticeable
    weights = [20, 30, 20, 15, 15]
    return random.choices(_USERS, weights=weights)[0]


def _normal_session(user: str, dt: datetime) -> dict:
    """Generate a plausible normal user session."""
    hour = dt.hour
    # Business-hours bias: most activity 9-17
    if 9 <= hour < 17:
        requests_pm = random.gauss(12, 4)
        transfer_mb = random.gauss(25, 12)
    else:
        requests_pm = random.gauss(3, 2)
        transfer_mb = random.gauss(5, 3)

    return {
        "user": user,
        "timestamp": dt.isoformat(),
        "login_hour": hour,
        "day_of_week": dt.weekday(),
        "requests_per_min": max(1, round(requests_pm, 1)),
        "transfer_mb": max(0.1, round(transfer_mb, 2)),
        "failed_logins": random.choices([0, 1, 2], weights=[85, 12, 3])[0],
        "unique_ips": random.choices([1, 2], weights=[90, 10])[0],
        "sensitive_accesses": random.choices([0, 1], weights=[95, 5])[0],
        "source": "normal",
    }


def _insider_threat_session(user: str, threat_type: str) -> dict:
    """Generate an anomalous insider threat session."""
    now = datetime.now(timezone.utc).replace(hour=2, minute=random.randint(0, 59))
    base = {
        "user": user,
        "timestamp": now.isoformat(),
        "login_hour": 2,
        "day_of_week": now.weekday(),
        "failed_logins": 0,   # Used valid creds — that's what makes insider threats dangerous
        "unique_ips": 1,
        "source": "insider_threat",
    }
    if threat_type == "data_exfiltration":
        base.update({
            "requests_per_min": 380,
            "transfer_mb": round(random.uniform(3500, 5000), 1),
            "sensitive_accesses": random.randint(30, 60),
        })
    elif threat_type == "credential_access":
        base.update({
            "requests_per_min": 25,
            "transfer_mb": round(random.uniform(0.5, 2.0), 2),
            "sensitive_accesses": random.randint(15, 40),
        })
    return base


def _generate_event(source: str, event_type: str, user: str, **kwargs) -> dict:
    return {"timestamp": _now_iso(), "source": source, "event_type": event_type,
            "user": user, **kwargs}


def _seed_historical_data():
    """Generate 30 days of normal sessions for training the anomaly detector."""
    now = datetime.now(timezone.utc)
    for day_offset in range(30, 0, -1):
        dt = now - timedelta(days=day_offset)
        for _ in range(random.randint(8, 20)):
            session_dt = dt.replace(hour=random.randint(7, 22),
                                    minute=random.randint(0, 59))
            user = _rand_user()
            session = _normal_session(user, session_dt)
            _SESSIONS.append(session)

            # Generate auth events
            _EVENTS.append(_generate_event("auth", "LOGIN_SUCCESS", user,
                                           ip=f"10.0.1.{random.randint(1, 20)}"))
            if session["failed_logins"] > 0:
                for _ in range(session["failed_logins"]):
                    _EVENTS.append(_generate_event("auth", "LOGIN_FAILURE", user,
                                                   ip=f"10.0.1.{random.randint(1, 20)}"))
            # Generate file events
            if session["sensitive_accesses"] > 0:
                _EVENTS.append(_generate_event("file", "READ", user,
                                               path=f"/etc/config/app_{random.randint(1,5)}.conf",
                                               bytes=random.randint(1024, 10240)))
            # Normal transfer events
            _EVENTS.append(_generate_event("network", "EGRESS", user,
                                           dst=f"10.0.0.{random.randint(1, 50)}",
                                           bytes=int(session["transfer_mb"] * 1024 * 1024)))

    # Trim to max size
    while len(_SESSIONS) > _MAX:
        _SESSIONS.pop(0)
    while len(_EVENTS) > _MAX * 3:
        _EVENTS.pop(0)


# Seed data on startup
_seed_historical_data()


def _background_metrics():
    """Update Prometheus metrics every 5 seconds."""
    while True:
        try:
            if _state["insider_threat_active"]:
                SIM_LOGIN_RATE.set(round(random.uniform(15, 25), 1))
                SIM_TRANSFER_MB.set(round(random.uniform(3000, 5000), 1))
                SIM_FAIL_LOGINS.set(0)
                SIM_ANOMALY.set(round(random.uniform(90, 99), 1))
            else:
                SIM_LOGIN_RATE.set(round(random.uniform(5, 15), 1))
                SIM_TRANSFER_MB.set(round(random.uniform(50, 200), 1))
                SIM_FAIL_LOGINS.set(random.randint(0, 3))
                SIM_ANOMALY.set(round(random.uniform(10, 35), 1))
        except Exception:
            pass
        time.sleep(5)


threading.Thread(target=_background_metrics, daemon=True).start()


# ── API Routes ─────────────────────────────────────────────────────────────────

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/")
def index():
    return jsonify({
        "service": "Module 12 — AIOps Security & Compliance Lab",
        "endpoints": [
            "GET  /metrics",
            "GET  /api/user-behavior",
            "GET  /api/siem-events",
            "GET  /api/state",
            "POST /api/inject-insider-threat",
            "POST /api/reset",
        ]
    })


@app.route("/api/user-behavior")
def user_behavior():
    """Return historical user sessions for anomaly detector training."""
    data = list(_SESSIONS)
    if _state["insider_threat_active"] and _state["threat_user"]:
        threat_session = _insider_threat_session(
            _state["threat_user"], _state["threat_type"] or "data_exfiltration"
        )
        data.append(threat_session)
    return jsonify(data)


@app.route("/api/siem-events")
def siem_events():
    """Return raw security events for SIEM correlation."""
    data = list(_EVENTS)
    if _state["insider_threat_active"] and _state["threat_user"]:
        user = _state["threat_user"]
        ts   = _now_iso()
        ext_ip = "203.0.113.42"  # RFC 5737 documentation IP
        data.extend([
            {**_generate_event("auth",    "LOGIN_SUCCESS", user, ip=ext_ip), "timestamp": ts},
            {**_generate_event("file",    "READ", user,
                               path="/opt/db/backups/prod_dump.sql.gz",
                               bytes=4_312_495_821), "timestamp": ts},
            {**_generate_event("network", "EGRESS", user,
                               dst=ext_ip, bytes=4_312_495_821), "timestamp": ts},
        ])
        for _ in range(44):
            data.append(_generate_event("file", "READ", user,
                                        path=random.choice([
                                            "/etc/passwd", "/root/.ssh/id_rsa",
                                            "/etc/shadow", "/opt/db/credentials.env"
                                        ]), bytes=random.randint(512, 8192)))
    return jsonify(data)


@app.route("/api/state")
def state():
    return jsonify({
        "insider_threat_active": _state["insider_threat_active"],
        "threat_user":           _state["threat_user"],
        "threat_type":           _state["threat_type"],
        "threat_start":          _state["threat_start"],
        "session_count":         len(_SESSIONS),
        "event_count":           len(_EVENTS),
    })


@app.route("/api/inject-insider-threat", methods=["POST"])
def inject_insider_threat():
    body = request.get_json(force=True, silent=True) or {}
    user        = body.get("user", "bob")
    threat_type = body.get("type", "data_exfiltration")

    if user not in _USERS:
        return jsonify({"error": f"Unknown user '{user}'. Valid: {_USERS}"}), 400

    _state["insider_threat_active"] = True
    _state["threat_user"]  = user
    _state["threat_type"]  = threat_type
    _state["threat_start"] = _now_iso()

    return jsonify({
        "status":  "injected",
        "user":    user,
        "type":    threat_type,
        "message": f"Insider threat session injected for '{user}'. Re-fetch /api/user-behavior and /api/siem-events."
    })


@app.route("/api/reset", methods=["POST"])
def reset():
    _state["insider_threat_active"] = False
    _state["threat_user"]  = None
    _state["threat_type"]  = None
    _state["threat_start"] = None
    return jsonify({"status": "reset", "message": "Insider threat cleared."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=False)
