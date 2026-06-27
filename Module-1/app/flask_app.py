"""
AIOps Lab — Sample Flask Application
Runs on app-server (192.168.56.11), behind Nginx reverse proxy.
Endpoints: /, /health, /api/status
"""
import socket
import time
from flask import Flask, jsonify

app = Flask(__name__)
START_TIME = time.time()


@app.route("/")
def home():
    return "<h1>AIOps Lab — App Server</h1><p>Flask is running on app-server.</p>"


@app.route("/health")
def health():
    return "OK"


@app.route("/api/status")
def status():
    uptime = round(time.time() - START_TIME, 2)
    return jsonify({
        "hostname": socket.gethostname(),
        "status": "healthy",
        "uptime_seconds": uptime,
        "service": "flask-app"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
