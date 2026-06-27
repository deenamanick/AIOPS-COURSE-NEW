# 04 — App Deployment (Flask + Nginx)

## What's Running on app-server

The provisioning script (`scripts/setup-app.sh`) already installs and starts:
- **Flask** app via Gunicorn (port 5000, localhost only)
- **Nginx** reverse proxy (port 80, public — forwards to Flask)

This lesson walks through what was set up and how to verify/modify it.

---

## Architecture

```
External Request → Nginx (:80) → Gunicorn (:5000) → Flask App
                                                        │
                                                   /, /health, /api/status
```

**Why Nginx in front of Flask?**
- Flask/Gunicorn is an application server — handles Python logic
- Nginx is a web server — handles static files, SSL termination, load balancing, connection buffering
- In production, you never expose Gunicorn directly

---

## Verify the Deployment

### From your host machine:

```bash
# Through port forwarding
curl http://localhost:8081/
curl http://localhost:8081/health
curl http://localhost:8081/api/status

# Through private network (direct VM IP)
curl http://192.168.56.11/
curl http://192.168.56.11/api/status
```

### From inside app-server:

```bash
vagrant ssh app-server

# Test Flask directly (bypassing Nginx)
curl http://127.0.0.1:5000/health

# Test through Nginx
curl http://localhost/api/status

# Check both services are running
systemctl status flask-app
systemctl status nginx
```

---

## The Flask App

Located at `/opt/flask-app/app.py` on app-server:

```python
@app.route("/")
def home():
    return "<h1>AIOps Lab — App Server</h1>"

@app.route("/health")
def health():
    return "OK"

@app.route("/api/status")
def status():
    return jsonify({
        "hostname": socket.gethostname(),
        "status": "healthy",
        "uptime_seconds": ...,
        "service": "flask-app"
    })
```

| Endpoint | Purpose | Response |
|---|---|---|
| `/` | Welcome page | HTML |
| `/health` | Health check (for monitoring) | `OK` (200) |
| `/api/status` | System status JSON | `{"hostname": "app-server", "status": "healthy", ...}` |

---

## The Nginx Config

Located at `/etc/nginx/sites-available/flask-proxy`:

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;     # Forward to Flask
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /nginx-status {
        stub_status on;                        # Nginx metrics endpoint
        allow 192.168.56.0/24;                 # Only accessible from lab network
        deny all;
    }
}
```

The `/nginx-status` endpoint will be useful when we add Prometheus monitoring in Module 6.

---

## Modify the App (Exercise)

SSH into `app-server` and add a new endpoint:

```bash
vagrant ssh app-server
sudo vim /opt/flask-app/app.py
```

Add a `/api/incidents` endpoint that returns a count:

```python
@app.route("/api/incidents")
def incidents():
    return jsonify({"total_incidents": 32, "source": "csv"})
```

Restart the app:
```bash
sudo systemctl restart flask-app
curl http://localhost/api/incidents
```

---

## Service Management

```bash
# View Flask app logs
journalctl -u flask-app -f

# Restart Flask
sudo systemctl restart flask-app

# Restart Nginx
sudo systemctl restart nginx

# Check Nginx config syntax
sudo nginx -t

# View Nginx access logs
tail -f /var/log/nginx/access.log

# View Nginx error logs
tail -f /var/log/nginx/error.log
```

---

## Concepts

| Concept | What it means |
|---|---|
| **Reverse proxy** | Server that sits in front of app servers, forwarding client requests |
| **Gunicorn** | Python WSGI HTTP server — runs Flask with multiple worker processes |
| **systemd service** | Linux service manager — starts, stops, restarts, monitors processes |
| **Health check endpoint** | Simple endpoint returning 200 OK — used by load balancers and monitoring |
| **stub_status** | Nginx module that exposes connection/request metrics |
