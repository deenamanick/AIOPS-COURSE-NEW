# 03 — Time-Window Alert Correlation

In Module 7, Alertmanager grouped alerts by label. That approach works when alerts share explicit labels such as `cluster` or `service`. In production, alerts often arrive from independent systems—monitoring, application logs, and user reports—without shared labels. Time-window correlation groups alerts that co-occur within a defined interval, regardless of their source.

---

## The Problem

A database becomes slow. Within two minutes, three independent monitoring systems fire:

```text
14:01  DB_LATENCY      (Prometheus → database team)
14:02  APP_5XX         (Prometheus → application team)
14:03  USER_COMPLAINTS (Support system → customer success)
```

Without correlation, three teams investigate three "incidents." With correlation, one incident is created and triage begins once.

---

## Correlation Algorithm

```text
1. Receive an alert event.
2. Check: does an open incident window exist within WINDOW_SECONDS?
   - YES → add the alert to that incident.
   - NO  → create a new incident with this alert.
3. When the window closes (no new alerts within WINDOW_SECONDS):
   - Finalize the incident.
   - Apply root-cause analysis (next lesson).
```

### Time Window

The window size is a trade-off:

| Window | Pro | Con |
|---|---|---|
| 30 seconds | Fast incident creation | Misses slow cascades |
| 2 minutes | Catches most cascading failures | Slightly delayed final grouping |
| 10 minutes | Catches everything | May merge unrelated incidents |

The lab uses a **120-second** (2-minute) window, which is the most common production default.

---

## The Correlation Engine

The lab includes `lab/correlation-engine/engine.py`:

```python
import time
from dataclasses import dataclass, field

WINDOW_SECONDS = 120

@dataclass
class Incident:
    id: int
    alerts: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_alert_at: float = field(default_factory=time.time)

    @property
    def is_open(self) -> bool:
        return (time.time() - self.last_alert_at) < WINDOW_SECONDS

    def add_alert(self, alert: dict):
        self.alerts.append(alert)
        self.last_alert_at = time.time()

class CorrelationEngine:
    def __init__(self):
        self.incidents: list[Incident] = []
        self._next_id = 1

    def ingest(self, alert: dict) -> Incident:
        # Find an open incident within the time window
        for incident in reversed(self.incidents):
            if incident.is_open:
                incident.add_alert(alert)
                return incident

        # No open incident — create a new one
        incident = Incident(id=self._next_id, alerts=[alert])
        self._next_id += 1
        self.incidents.append(incident)
        return incident
```

Each alert is a dictionary with at minimum:

```python
{
    "alertname": "DB_LATENCY",
    "severity": "critical",
    "service": "postgres",
    "timestamp": "2026-08-06T14:01:00Z",
    "summary": "Database query latency > 500ms for 5 minutes"
}
```

---

## Lab: Correlate Three Alerts

```bash
cd Module-8/lab
docker compose up -d --build
```

The lab's correlation engine listens for alert events on a lightweight pub/sub bus. Trigger the cascade:

```bash
# Simulate the database going slow
curl -X POST http://localhost:5000/drill/db-slow

# Wait 60 seconds, then send mixed traffic to trigger APP_5XX
sleep 60
for i in $(seq 1 100); do
  curl -s http://localhost:8080/api/users > /dev/null
done
```

The correlation engine receives the following alerts within a 2-minute window:

```text
Input:
  [Alert: DB_LATENCY    @ 14:01]
  [Alert: APP_5XX       @ 14:02]
  [Alert: USER_IMPACT   @ 14:03]

Output:
  Incident #1 — 3 correlated alerts
```

View the engine output:

```bash
docker compose logs -f correlation-engine
```

Expected output:

```text
[CORRELATOR] New incident #1 created — trigger: DB_LATENCY
[CORRELATOR] Alert APP_5XX added to incident #1 (2 alerts, window open)
[CORRELATOR] Alert USER_IMPACT added to incident #1 (3 alerts, window open)
[CORRELATOR] Incident #1 closed — 3 alerts correlated in 120s window
```

---

## Correlation vs Grouping vs Deduplication

| Mechanism | What it does | Where it lives |
|---|---|---|
| Deduplication | Suppresses identical repeat alerts | Alertmanager `repeat_interval` |
| Grouping | Combines alerts sharing labels | Alertmanager `group_by` |
| Correlation | Groups alerts by time proximity across sources | Correlation engine (this module) |
| Root-cause analysis | Identifies the originating failure | Dependency graph (next lesson) |

These are complementary, not competing. Production systems typically run all four.

---

## Debrief

- How many separate notifications would three teams receive without correlation?
- What happens if you set the window to 10 seconds? (Try it: change `WINDOW_SECONDS` in the engine.)
- What happens if two genuinely unrelated incidents occur within 2 minutes?
- How would you handle the false-merge problem in production?

In the next lesson, you will add a dependency graph so the correlation engine can identify which of the grouped alerts is the root cause.
