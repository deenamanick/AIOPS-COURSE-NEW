"""Instrumented service with controls for Module 8 log analytics & correlation drills."""

import time
import random
import threading
from flask import Flask, Response, request, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

app = Flask(__name__)
REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
DURATION = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"])
DB_SLOW = Gauge("training_db_slow", "Whether the database slowness drill is active")
DISK_FULL = Gauge("training_disk_full", "Whether the disk-full drill is active")
CONN_POOL = Gauge("training_conn_pool_used", "Simulated connection pool usage percent")

# Drill state
_drill_state = {
    "db_slow": False,
    "disk_full": False,
}


@app.before_request
def start_timer():
    request.start_time = time.perf_counter()


@app.after_request
def record_request(response):
    if request.path != "/metrics":
        endpoint = request.url_rule.rule if request.url_rule else "unknown"
        REQUESTS.labels(request.method, endpoint, str(response.status_code)).inc()
        DURATION.labels(request.method, endpoint).observe(time.perf_counter() - request.start_time)
    return response


@app.get("/")
def index():
    return jsonify({"service": "module-8-training", "status": "ok"})


@app.get("/health")
def health():
    return jsonify({"status": "healthy"})


@app.get("/api/users")
def api_users():
    if _drill_state["disk_full"]:
        CONN_POOL.set(100)
        time.sleep(random.uniform(2.0, 5.0))  # Simulate connection pool wait
        return jsonify({"error": "database connection pool exhausted"}), 503

    if _drill_state["db_slow"]:
        CONN_POOL.set(random.randint(70, 95))
        time.sleep(random.uniform(0.5, 2.0))  # Simulate slow queries
        if random.random() < 0.3:
            return jsonify({"error": "database query timeout"}), 503

    CONN_POOL.set(random.randint(10, 40))
    users = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Carol"},
    ]
    return jsonify(users)


@app.get("/api/orders")
def api_orders():
    if _drill_state["disk_full"]:
        time.sleep(random.uniform(1.0, 3.0))
        return jsonify({"error": "write failed — disk full"}), 503

    if _drill_state["db_slow"]:
        time.sleep(random.uniform(0.3, 1.5))

    return jsonify([{"id": 101, "item": "Widget", "qty": 3}])


@app.get("/slow")
def slow():
    delay = random.uniform(0.5, 2.0)
    time.sleep(delay)
    return jsonify({"delayed_ms": int(delay * 1000)})


@app.get("/error")
def error():
    return jsonify({"error": "simulated failure"}), 500


# --- Drill Endpoints ---

@app.post("/drill/db-slow")
def drill_db_slow():
    _drill_state["db_slow"] = True
    DB_SLOW.set(1)
    # Simulate alert generation after a delay
    threading.Timer(5.0, _emit_alert, args=("DB_LATENCY", "postgres", "critical",
        "Database query latency > 500ms for 5 minutes")).start()
    return jsonify({"drill": "db-slow", "active": True})


@app.post("/drill/disk-full")
def drill_disk_full():
    _drill_state["disk_full"] = True
    _drill_state["db_slow"] = True
    DISK_FULL.set(1)
    DB_SLOW.set(1)
    # Emit cascading alerts with realistic delays
    threading.Timer(2.0, _emit_alert, args=("DISK_PRESSURE", "postgres", "critical",
        "Disk usage > 95% on postgres")).start()
    threading.Timer(8.0, _emit_alert, args=("DB_WRITE_FAILURE", "postgres", "critical",
        "Database write errors > 0")).start()
    threading.Timer(15.0, _emit_alert, args=("CONN_POOL_EXHAUSTED", "flask-app", "critical",
        "Connection pool at 100%")).start()
    threading.Timer(25.0, _emit_alert, args=("APP_5XX", "flask-app", "critical",
        "HTTP 5xx error rate > 5% for 2m")).start()
    threading.Timer(35.0, _emit_alert, args=("USER_IMPACT", "nginx", "warning",
        "User-facing error rate elevated")).start()
    return jsonify({"drill": "disk-full", "active": True, "cascade": "5 alerts over 35 seconds"})


@app.post("/drill/reset")
def drill_reset():
    _drill_state["db_slow"] = False
    _drill_state["disk_full"] = False
    DB_SLOW.set(0)
    DISK_FULL.set(0)
    CONN_POOL.set(0)
    return jsonify({"drill": "reset", "active": False})


def _emit_alert(alertname: str, service: str, severity: str, summary: str):
    """Write alert event to a shared file that the correlation engine watches."""
    import json, os
    event = {
        "alertname": alertname,
        "service": service,
        "severity": severity,
        "summary": summary,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    alert_file = "/data/incoming_alerts.jsonl"
    os.makedirs(os.path.dirname(alert_file), exist_ok=True)
    with open(alert_file, "a") as f:
        f.write(json.dumps(event) + "\n")


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
