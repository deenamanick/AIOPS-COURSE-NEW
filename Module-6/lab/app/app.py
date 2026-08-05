"""Small instrumented Flask service for the Module 6 observability lab."""

import logging
import os
import time

from flask import Flask, Response, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = Flask(__name__)

log_file = os.environ.get("APP_LOG_FILE", "app.log")
os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)sZ %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger("observability-lab")

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)


@app.before_request
def start_timer():
    request.start_time = time.perf_counter()


@app.after_request
def record_request(response):
    if request.path != "/metrics":
        elapsed = time.perf_counter() - request.start_time
        endpoint = request.url_rule.rule if request.url_rule else "unknown"
        REQUESTS.labels(request.method, endpoint, str(response.status_code)).inc()
        DURATION.labels(request.method, endpoint).observe(elapsed)
        logger.info("method=%s path=%s status=%s duration=%.4f", request.method, request.path, response.status_code, elapsed)
    return response


@app.get("/")
def index():
    return {"service": "aiops-observability-lab", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/error")
def error():
    logger.error("simulated application failure path=/error reason=training_drill")
    return {"error": "simulated failure"}, 500


@app.get("/slow")
def slow():
    time.sleep(1)
    return {"status": "slow response completed"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
