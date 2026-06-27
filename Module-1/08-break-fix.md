# 08 — Break/Fix Exercises

Hands-on troubleshooting practice. For each exercise: **Break** → **Detect** → **Diagnose** → **Fix** → **Verify**.

---

## Exercise 1: Stop Nginx

### Break
```bash
vagrant ssh app-server
sudo systemctl stop nginx
```

### Detect
```bash
# From host
curl http://localhost:8081/health
# → curl: (7) Failed to connect to localhost port 8081: Connection refused
```

### Diagnose
```bash
# Is Nginx running?
systemctl status nginx
# → inactive (dead)

# Is anything listening on port 80?
ss -tlnp | grep ":80"
# → (nothing)

# Check Nginx logs for errors
journalctl -u nginx -n 20
```

### Fix
```bash
sudo systemctl start nginx
```

### Verify
```bash
curl http://localhost:8081/health
# → OK

systemctl is-active nginx
# → active
```

---

## Exercise 2: Disk Full Simulation

### Break
```bash
vagrant ssh app-server

# Create a large file to fill /tmp
dd if=/dev/zero of=/tmp/disk_fill bs=1M count=500
```

### Detect
```bash
df -h /tmp
# → /tmp usage jumps significantly
```

### Diagnose
```bash
# Find what's consuming space
du -sh /tmp/*
# → /tmp/disk_fill    500M

# In real life, check log directories
du -sh /var/log/*
```

### Fix
```bash
rm /tmp/disk_fill
```

### Verify
```bash
df -h /tmp
# → Usage dropped back to normal
```

---

## Exercise 3: Kill Flask Process

### Break
```bash
vagrant ssh app-server

# Find and kill the Flask/Gunicorn process
sudo pkill -f gunicorn
```

### Detect
```bash
# Nginx is running but Flask is dead
curl http://localhost:8081/
# → 502 Bad Gateway

# Key insight: 502 = Nginx is up but upstream (Flask) is down
```

### Diagnose
```bash
# Is Flask running?
systemctl status flask-app
# → failed / inactive

# Check Flask logs
journalctl -u flask-app -n 20

# Is anything on port 5000?
ss -tlnp | grep 5000
# → (nothing)
```

### Fix
```bash
sudo systemctl start flask-app
```

### Verify
```bash
curl http://localhost:8081/health
# → OK

curl http://localhost:8081/api/status
# → {"hostname": "app-server", "status": "healthy", ...}
```

---

## Exercise 4: Stop RAG Demo Container

### Break
```bash
vagrant ssh aiops-control
cd /opt/rag-demo

docker compose stop rag-app
```

### Detect
```bash
# From host browser: http://localhost:8501 → connection refused

# Check from host
curl http://localhost:8501
# → curl: (7) Failed to connect
```

### Diagnose
```bash
# Check container status
docker compose ps
# → rag-app shows "Exited"

# Check logs for errors
docker compose logs rag-app
```

### Fix
```bash
docker compose start rag-app

# Or if something is corrupted:
docker compose up -d --build rag-app
```

### Verify
```bash
docker compose ps
# → rag-app shows "Up (healthy)"

curl -s http://localhost:8501 | head -5
# → HTML output from Streamlit
```

---

## Exercise 5: CPU Stress (Bonus)

### Break
```bash
vagrant ssh app-server

# Install stress tool
sudo apt-get install -y stress-ng

# Spike CPU to 100% for 60 seconds
stress-ng --cpu 0 --timeout 60s &
```

### Detect
```bash
# In another terminal
vagrant ssh app-server

# Watch CPU in real-time
top
# → CPU usage at 95-100%

# Check load average
uptime
# → load average: 4.00, 2.50, 1.00  (high for a 1-CPU VM)
```

### Diagnose
```bash
# Find the stress process
ps aux | grep stress
# → stress-ng processes consuming CPU

# Check if it's affecting the app
curl -w "Time: %{time_total}s\n" http://localhost/health
# → Response time may increase
```

### Fix
```bash
# Kill the stress test
pkill -f stress-ng
```

### Verify
```bash
top
# → CPU usage drops back to normal

uptime
# → load average decreasing
```

---

## Summary Table

| Exercise | What broke | How you detected | Key command |
|---|---|---|---|
| Nginx stopped | Connection refused on :80 | `systemctl status nginx` | `systemctl start nginx` |
| Disk full | Application errors / writes fail | `df -h` | `rm <large file>` |
| Flask killed | Nginx returns 502 | `systemctl status flask-app` | `systemctl start flask-app` |
| Container stopped | Streamlit UI unreachable | `docker compose ps` | `docker compose start rag-app` |
| CPU stress | Slow responses, high load | `top`, `uptime` | `pkill stress-ng` |

---

## Key Takeaway

The diagnostic pattern is always the same:
1. **What's the symptom?** (connection refused, 502, slow response)
2. **Is the service running?** (`systemctl status`, `docker compose ps`)
3. **What do the logs say?** (`journalctl`, `docker compose logs`)
4. **What's the resource state?** (`top`, `free -m`, `df -h`, `ss -tlnp`)
5. **Fix and verify** (restart service, clean disk, kill rogue process)
