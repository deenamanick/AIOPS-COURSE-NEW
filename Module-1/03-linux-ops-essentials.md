# 03 — Linux Ops Essentials

Quick reference of essential Linux commands for IT operations. Run these on any of your lab VMs.

---

## Resource Monitoring

### CPU & Processes

```bash
# Real-time process viewer — CPU, memory, PID
top

# Better version (interactive, color, tree view)
htop

# System uptime and load averages (1, 5, 15 min)
uptime

# Number of CPU cores
nproc

# CPU info
lscpu | grep -E "^(CPU|Thread|Core|Socket|Model name)"
```

### Memory

```bash
# Memory usage in MB
free -m

# Breakdown:
#   total    = physical RAM
#   used     = actively in use
#   free     = completely unused
#   available = free + reclaimable cache (THIS is what matters)
```

### Disk

```bash
# Disk usage (human readable)
df -h

# Directory size
du -sh /var/log

# Find large files (>100MB)
find / -type f -size +100M 2>/dev/null
```

---

## Service Management (systemd)

```bash
# Check service status
systemctl status nginx

# Start / Stop / Restart
systemctl start nginx
systemctl stop nginx
systemctl restart nginx

# Enable on boot / Disable
systemctl enable nginx
systemctl disable nginx

# List all running services
systemctl list-units --type=service --state=running

# Check if a service is active
systemctl is-active nginx
```

---

## Log Investigation (journalctl)

```bash
# Logs for a specific service
journalctl -u nginx

# Last 50 lines
journalctl -u nginx -n 50

# Follow (tail) logs in real time
journalctl -u nginx -f

# Logs since a time window
journalctl -u nginx --since "5 minutes ago"
journalctl -u nginx --since "2024-01-15 14:00" --until "2024-01-15 15:00"

# Only errors
journalctl -u nginx -p err

# Kernel messages (useful for OOM kills)
journalctl -k
```

---

## Network Debugging

```bash
# Show listening ports and associated processes
ss -tlnp

# Breakdown:
#   -t = TCP only
#   -l = listening sockets only
#   -n = show port numbers (not service names)
#   -p = show process using the port

# Test HTTP endpoint
curl -v http://192.168.56.11/health

# Test connectivity
ping -c 3 192.168.56.11

# DNS resolution
dig google.com
nslookup google.com

# Show IP addresses
ip addr show

# Show routing table
ip route
```

---

## Process Management

```bash
# Find a process by name
ps aux | grep flask

# Kill a process by PID
kill <PID>

# Force kill
kill -9 <PID>

# Kill by name
pkill -f flask_app
```

---

## Quick Reference Table

| Command | Purpose | When to use |
|---|---|---|
| `top` / `htop` | CPU & memory usage | "Is something eating CPU?" |
| `free -m` | Memory breakdown | "Are we running out of RAM?" |
| `df -h` | Disk usage | "Is the disk full?" |
| `systemctl status <svc>` | Service health | "Is nginx running?" |
| `journalctl -u <svc> -f` | Live logs | "What's happening right now?" |
| `ss -tlnp` | Listening ports | "Is the app actually listening?" |
| `curl -v <url>` | HTTP test | "Can I reach the endpoint?" |
| `ping` | Network reachability | "Can VM A talk to VM B?" |

---

## Stress Testing Tools (used in Break/Fix)

```bash
# Install stress tools
sudo apt-get install -y stress-ng

# CPU stress (4 cores, 30 seconds)
stress-ng --cpu 4 --timeout 30s

# Memory stress (allocate 512MB, 30 seconds)
stress-ng --vm 2 --vm-bytes 512M --timeout 30s

# Disk fill (create a 500MB file in /tmp)
dd if=/dev/zero of=/tmp/fill_disk bs=1M count=500
```
