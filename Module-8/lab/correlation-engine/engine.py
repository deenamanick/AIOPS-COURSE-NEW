"""
Module 8 — Correlation Engine with Pub/Sub, Dependency Graph, and RCA.

Watches /data/incoming_alerts.jsonl for new alert events, publishes them
to an in-process event bus, and runs three subscribers:
  1. File Logger — writes to /data/alert_events.jsonl
  2. Correlation Engine — groups co-occurring alerts into incidents
  3. Notifier — prints critical alerts with severity-based formatting

When an incident window closes, the RCA module walks the dependency graph
to identify root cause vs symptoms.
"""

import json
import os
import queue
import threading
import time
from dataclasses import dataclass, field
from collections import Counter

# ─── Configuration ───────────────────────────────────────────────────────────

WINDOW_SECONDS = 120
ALERT_FILE = "/data/incoming_alerts.jsonl"
EVENT_LOG = "/data/alert_events.jsonl"

# ─── Dependency Graph ────────────────────────────────────────────────────────

DEPENDENCY_MAP = {
    "user-frontend": ["nginx"],
    "nginx": ["flask-app"],
    "flask-app": ["postgres", "redis"],
    "postgres": [],
    "redis": [],
}


def get_depth(service: str, graph: dict, cache: dict = None) -> int:
    if cache is None:
        cache = {}
    if service in cache:
        return cache[service]
    deps = graph.get(service, [])
    if not deps:
        cache[service] = 0
        return 0
    depth = 1 + max(get_depth(d, graph, cache) for d in deps)
    cache[service] = depth
    return depth


def identify_root_cause(alerts: list, graph: dict) -> dict:
    alert_depths = []
    for alert in alerts:
        service = alert.get("service", "unknown")
        depth = get_depth(service, graph)
        alert_depths.append((depth, alert))

    alert_depths.sort(key=lambda x: x[0])

    root_cause = alert_depths[0][1]
    symptoms = [a[1] for d, a in alert_depths[1:]]

    return {
        "root_cause": root_cause["alertname"],
        "root_service": root_cause["service"],
        "symptoms": [a["alertname"] for a in symptoms],
        "reasoning": f"{root_cause['service']} is the deepest alerting dependency",
    }


# ─── Correlation Engine ──────────────────────────────────────────────────────

@dataclass
class Incident:
    id: int
    alerts: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_alert_at: float = field(default_factory=time.time)
    closed: bool = False

    @property
    def is_open(self) -> bool:
        return not self.closed and (time.time() - self.last_alert_at) < WINDOW_SECONDS

    def add_alert(self, alert: dict):
        self.alerts.append(alert)
        self.last_alert_at = time.time()


class CorrelationEngine:
    def __init__(self):
        self.incidents: list[Incident] = []
        self._next_id = 1

    def ingest(self, alert: dict) -> Incident:
        for incident in reversed(self.incidents):
            if incident.is_open:
                incident.add_alert(alert)
                return incident

        incident = Incident(id=self._next_id, alerts=[alert])
        self._next_id += 1
        self.incidents.append(incident)
        return incident

    def check_closed(self):
        for incident in self.incidents:
            if not incident.closed and not incident.is_open and len(incident.alerts) > 0:
                incident.closed = True
                return incident
        return None


# ─── Event Bus (Pub/Sub) ─────────────────────────────────────────────────────

class EventBus:
    def __init__(self):
        self._subscribers: list[queue.Queue] = []

    def subscribe(self) -> queue.Queue:
        q = queue.Queue()
        self._subscribers.append(q)
        return q

    def publish(self, event: dict):
        for q in self._subscribers:
            q.put(event)

    def start_consumer(self, name: str, q: queue.Queue, handler):
        def _consume():
            while True:
                event = q.get()
                try:
                    handler(event)
                except Exception as e:
                    print(f"[{name}] Error: {e}", flush=True)
        t = threading.Thread(target=_consume, name=name, daemon=True)
        t.start()
        return t


# ─── Subscribers ──────────────────────────────────────────────────────────────

correlation_engine = CorrelationEngine()
severity_counts = Counter()


def file_logger(event: dict):
    os.makedirs(os.path.dirname(EVENT_LOG), exist_ok=True)
    with open(EVENT_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")
    print(f"[FILE-LOGGER] Logged: {event['alertname']}", flush=True)


def correlator_handler(event: dict):
    incident = correlation_engine.ingest(event)
    alert_count = len(incident.alerts)
    status = "window open" if incident.is_open else "window closed"
    print(f"[CORRELATOR]  {event['alertname']} → Incident #{incident.id} "
          f"({alert_count} alerts, {status})", flush=True)


def notifier(event: dict):
    if event.get("severity") == "critical":
        print(f"[NOTIFIER]    🚨 CRITICAL: {event['alertname']} — {event['summary']}", flush=True)
    else:
        print(f"[NOTIFIER]    ℹ️  {event.get('severity', 'info')}: "
              f"{event['alertname']} — {event.get('summary', '')}", flush=True)


def metrics_exporter(event: dict):
    severity_counts[event.get("severity", "unknown")] += 1
    print(f"[METRICS]     Severity counts: {dict(severity_counts)}", flush=True)


# ─── Incident Closer (Background Thread) ─────────────────────────────────────

def incident_closer():
    while True:
        closed = correlation_engine.check_closed()
        if closed:
            print(f"\n[CORRELATOR]  Incident #{closed.id} closed — "
                  f"{len(closed.alerts)} alerts correlated in {WINDOW_SECONDS}s window",
                  flush=True)

            # Run RCA
            print(f"[RCA] Analyzing incident #{closed.id}...", flush=True)
            depth_cache = {}
            for alert in closed.alerts:
                svc = alert.get("service", "unknown")
                depth = get_depth(svc, DEPENDENCY_MAP, depth_cache)
                print(f"[RCA]   {alert['alertname']:<25} → service: {svc:<12} (depth: {depth})",
                      flush=True)

            result = identify_root_cause(closed.alerts, DEPENDENCY_MAP)
            print(f"[RCA] {'─' * 55}", flush=True)
            print(f"[RCA] ROOT CAUSE:  {result['root_cause']} ({result['root_service']})",
                  flush=True)
            print(f"[RCA] SYMPTOMS:    {', '.join(result['symptoms'])}", flush=True)
            print(f"[RCA] REASONING:   {result['reasoning']}\n", flush=True)

        time.sleep(5)


# ─── File Watcher (Tail incoming_alerts.jsonl) ────────────────────────────────

def watch_alerts(bus: EventBus):
    os.makedirs(os.path.dirname(ALERT_FILE), exist_ok=True)
    # Create file if it doesn't exist
    if not os.path.exists(ALERT_FILE):
        open(ALERT_FILE, "w").close()

    with open(ALERT_FILE, "r") as f:
        # Seek to end
        f.seek(0, 2)
        while True:
            line = f.readline()
            if line:
                line = line.strip()
                if line:
                    try:
                        event = json.loads(line)
                        bus.publish(event)
                    except json.JSONDecodeError:
                        print(f"[WATCHER] Invalid JSON: {line}", flush=True)
            else:
                time.sleep(0.5)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60, flush=True)
    print("  Module 8 — Correlation Engine with Pub/Sub & RCA", flush=True)
    print(f"  Window: {WINDOW_SECONDS}s | Watching: {ALERT_FILE}", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    bus = EventBus()

    # Subscribe all consumers
    file_q = bus.subscribe()
    corr_q = bus.subscribe()
    notify_q = bus.subscribe()
    metrics_q = bus.subscribe()

    bus.start_consumer("file-logger", file_q, file_logger)
    bus.start_consumer("correlator", corr_q, correlator_handler)
    bus.start_consumer("notifier", notify_q, notifier)
    bus.start_consumer("metrics-exporter", metrics_q, metrics_exporter)

    # Start incident closer
    threading.Thread(target=incident_closer, daemon=True).start()

    # Start file watcher (blocks)
    print("[WATCHER] Waiting for alert events...\n", flush=True)
    watch_alerts(bus)


if __name__ == "__main__":
    main()
