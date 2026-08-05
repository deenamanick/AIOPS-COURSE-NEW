"""Instrumented service with safe controls for Module 7 failure drills."""

import time
from flask import Flask, Response, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

app = Flask(__name__)
REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
DURATION = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"])
DATABASE_DOWN = Gauge("training_database_down", "Whether the training database drill is active")


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
    return {"service": "module-7-training", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/error")
def error():
    return {"error": "simulated failure"}, 500


@app.post("/drill/db-down")
def db_down():
    DATABASE_DOWN.set(1)
    return {"training_database_down": 1}


@app.post("/drill/reset")
def reset():
    DATABASE_DOWN.set(0)
    return {"training_database_down": 0}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
