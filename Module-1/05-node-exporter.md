# 05 — Node Exporter (Prometheus Monitoring Agent)

## What is Node Exporter?

**Node Exporter** is a Prometheus agent that runs on every server and exposes system-level metrics (CPU, memory, disk, network) as an HTTP endpoint. Prometheus scrapes this endpoint periodically to collect time-series data.

```
Node Exporter (:9100/metrics) → Prometheus scrapes → Grafana visualizes
```

In Module 1, we install Node Exporter on both VMs to **lay the foundation** for full Prometheus + Grafana monitoring in Module 6.

---

## Verify Node Exporter

The provisioning scripts already installed and started Node Exporter on both VMs.

### From your host:

```bash
# aiops-control (forwarded to host port 9100)
curl -s http://localhost:9100/metrics | head -20

# app-server (forwarded to host port 9101)
curl -s http://localhost:9101/metrics | head -20

# Or via private network IPs
curl -s http://192.168.56.10:9100/metrics | head -20
curl -s http://192.168.56.11:9100/metrics | head -20
```

### From inside any VM:

```bash
vagrant ssh aiops-control
curl -s localhost:9100/metrics | head -20

# Check the service
systemctl status node_exporter
```

---

## Key Metrics to Know

Node Exporter exposes hundreds of metrics. Here are the essential ones for AIOps:

### CPU

```bash
# CPU time spent in each mode (idle, user, system, iowait)
curl -s localhost:9100/metrics | grep "node_cpu_seconds_total"
```

To calculate CPU usage: `100 - (idle_seconds / total_seconds * 100)`

### Memory

```bash
# Total memory
curl -s localhost:9100/metrics | grep "node_memory_MemTotal_bytes"

# Available memory (what can be used by new processes)
curl -s localhost:9100/metrics | grep "node_memory_MemAvailable_bytes"
```

### Disk

```bash
# Available bytes per filesystem
curl -s localhost:9100/metrics | grep "node_filesystem_avail_bytes"

# Total bytes per filesystem
curl -s localhost:9100/metrics | grep "node_filesystem_size_bytes"
```

### Network

```bash
# Bytes received/transmitted per interface
curl -s localhost:9100/metrics | grep "node_network_receive_bytes_total"
curl -s localhost:9100/metrics | grep "node_network_transmit_bytes_total"
```

### System

```bash
# System uptime (seconds since boot)
curl -s localhost:9100/metrics | grep "node_boot_time_seconds"

# System load averages (1, 5, 15 min)
curl -s localhost:9100/metrics | grep "node_load"
```

---

## Metric Format

Prometheus metrics follow a specific text format:

```
# HELP node_cpu_seconds_total Seconds the CPUs spent in each mode.
# TYPE node_cpu_seconds_total counter
node_cpu_seconds_total{cpu="0",mode="idle"} 1234.56
node_cpu_seconds_total{cpu="0",mode="user"} 789.01
```

| Part | Meaning |
|---|---|
| `# HELP` | Description of the metric |
| `# TYPE` | Metric type: counter, gauge, histogram, summary |
| `node_cpu_seconds_total` | Metric name |
| `{cpu="0",mode="idle"}` | Labels (dimensions) |
| `1234.56` | Current value |

### Metric Types

| Type | Description | Example |
|---|---|---|
| **Counter** | Only goes up (resets on restart) | Total HTTP requests, CPU seconds |
| **Gauge** | Goes up and down | Current memory usage, temperature |
| **Histogram** | Distribution of values in buckets | Request duration |
| **Summary** | Like histogram but with quantiles | P50, P90, P99 latency |

---

## Exercise: Compare Metrics Across VMs

```bash
# Get available memory on both VMs
echo "aiops-control:"
curl -s http://192.168.56.10:9100/metrics | grep "node_memory_MemAvailable_bytes" | grep -v "#"

echo "app-server:"
curl -s http://192.168.56.11:9100/metrics | grep "node_memory_MemAvailable_bytes" | grep -v "#"
```

This is exactly what Prometheus automates — scraping these metrics from all targets every 15 seconds and storing them in a time-series database.

---

## What's Next

In **Module 6 (Observability)**, we'll:
1. Install Prometheus to scrape Node Exporter from both VMs
2. Build Grafana dashboards to visualize CPU, memory, disk in real-time
3. Add Loki for log aggregation
4. Write PromQL queries to create alerts
