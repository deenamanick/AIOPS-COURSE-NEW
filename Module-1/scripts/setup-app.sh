#!/bin/bash
# =============================================================================
# AIOps Module 1 — app-server VM Provisioning
# Installs: Python3, Flask, Nginx (reverse proxy), Node Exporter
# =============================================================================

set -e

echo ">>> Updating system packages..."
apt-get update -y
apt-get install -y python3 python3-pip python3-venv nginx curl

# --- Flask App ---
echo ">>> Setting up Flask application..."
mkdir -p /opt/flask-app
cd /opt/flask-app

python3 -m venv venv

cat > requirements.txt <<EOF
flask==3.0.3
gunicorn==22.0.0
EOF

/opt/flask-app/venv/bin/pip install -r requirements.txt

cat > app.py <<'PYEOF'
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
PYEOF

# Create systemd service for Flask (via Gunicorn)
cat > /etc/systemd/system/flask-app.service <<EOF
[Unit]
Description=Flask AIOps App (Gunicorn)
After=network.target

[Service]
User=vagrant
WorkingDirectory=/opt/flask-app
ExecStart=/opt/flask-app/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable flask-app
systemctl start flask-app

# --- Nginx Reverse Proxy ---
echo ">>> Configuring Nginx reverse proxy..."
cat > /etc/nginx/sites-available/flask-proxy <<'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /nginx-status {
        stub_status on;
        allow 192.168.56.0/24;
        deny all;
    }
}
NGINX

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/flask-proxy /etc/nginx/sites-enabled/flask-proxy
nginx -t
systemctl restart nginx

# --- Node Exporter ---
echo ">>> Installing Node Exporter..."
NODE_EXPORTER_VERSION="1.7.0"
cd /tmp
curl -LO "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar xzf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
cp "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" /usr/local/bin/

cat > /etc/systemd/system/node_exporter.service <<EOF
[Unit]
Description=Prometheus Node Exporter
After=network.target

[Service]
User=nobody
ExecStart=/usr/local/bin/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter

chown -R vagrant:vagrant /opt/flask-app

echo ">>> app-server provisioning complete!"
echo "    Flask:          http://127.0.0.1:5000"
echo "    Nginx:          http://192.168.56.11"
echo "    Node Exporter:  http://192.168.56.11:9100/metrics"
