"""Local Alertmanager webhook sink used only for training."""

from collections import deque
from datetime import datetime, timezone
from flask import Flask, jsonify, request

app = Flask(__name__)
received = deque(maxlen=100)


@app.post("/alert")
def alert():
    received.appendleft({"received_at": datetime.now(timezone.utc).isoformat(), "payload": request.get_json()})
    return {"accepted": True}, 202


@app.get("/alerts")
def alerts():
    return jsonify(list(received))


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
