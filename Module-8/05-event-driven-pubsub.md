# 05 — Event-Driven Architecture Lab

In previous lessons, the correlation engine received alerts directly. In production, alert sources are diverse—Prometheus, application logs, support tickets, cloud provider health—and they should not know about each other. An event-driven architecture decouples **producers** (alert sources) from **consumers** (correlation engine, logger, notifier) using a message bus.

---

## The Core Principle

> "Events decouple producers from consumers."

A producer publishes an event to a topic. It does not know—or care—how many consumers exist, what they do, or whether they are running. Consumers subscribe to the topic and react independently.

```text
                    ┌─── Subscriber 1: File Logger
                    │
Publisher ──► Bus ──┼─── Subscriber 2: Correlation Engine
                    │
                    └─── Subscriber 3: Notifier (Slack/Email)
```

Adding a fourth subscriber (e.g., metrics exporter) requires zero changes to the publisher.

---

## Pub/Sub in Python

The lab implements a lightweight in-process pub/sub using Python's `queue.Queue`. This is not production-grade (no persistence, no distribution), but it teaches the pattern before introducing Kafka or Redis Pub/Sub.

```python
import queue
import threading
from typing import Callable

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

    def start_consumer(self, name: str, q: queue.Queue, handler: Callable):
        def _consume():
            while True:
                event = q.get()
                try:
                    handler(event)
                except Exception as e:
                    print(f"[{name}] Error: {e}")
        t = threading.Thread(target=_consume, name=name, daemon=True)
        t.start()
        return t
```

---

## The Three Subscribers

### Subscriber 1: File Logger

Writes every event to a JSON Lines file for auditing and replay:

```python
import json

def file_logger(event: dict):
    with open("/data/alert_events.jsonl", "a") as f:
        f.write(json.dumps(event) + "\n")
    print(f"[FILE-LOGGER] Logged: {event['alertname']}")
```

### Subscriber 2: Correlation Engine

Feeds events to the `CorrelationEngine` from Lesson 03:

```python
def correlator_handler(event: dict):
    incident = correlation_engine.ingest(event)
    print(f"[CORRELATOR] {event['alertname']} → Incident #{incident.id} "
          f"({len(incident.alerts)} alerts)")
```

### Subscriber 3: Notifier

Sends a notification for critical alerts:

```python
def notifier(event: dict):
    if event.get("severity") == "critical":
        print(f"[NOTIFIER] 🚨 CRITICAL: {event['alertname']} — {event['summary']}")
    else:
        print(f"[NOTIFIER] ℹ️  {event['severity']}: {event['alertname']}")
```

---

## Lab: Run the Pub/Sub Pipeline

```bash
cd Module-8/lab
docker compose up -d --build
```

The correlation engine container runs all three subscribers on the same event bus. Trigger events:

```bash
# Trigger the cascading failure
curl -X POST http://localhost:5000/drill/db-slow

# Generate traffic to surface downstream alerts
sleep 60
for i in $(seq 1 100); do
  curl -s http://localhost:8080/api/users > /dev/null
done
```

Watch all three subscribers process the same events:

```bash
docker compose logs -f correlation-engine
```

Expected output:

```text
[FILE-LOGGER] Logged: DB_LATENCY
[CORRELATOR]  DB_LATENCY → Incident #1 (1 alerts)
[NOTIFIER]    🚨 CRITICAL: DB_LATENCY — Database query latency > 500ms for 5m

[FILE-LOGGER] Logged: APP_5XX
[CORRELATOR]  APP_5XX → Incident #1 (2 alerts)
[NOTIFIER]    🚨 CRITICAL: APP_5XX — HTTP 5xx error rate > 5% for 2m

[FILE-LOGGER] Logged: USER_IMPACT
[CORRELATOR]  USER_IMPACT → Incident #1 (3 alerts)
[NOTIFIER]    ℹ️  warning: USER_IMPACT — User-facing error rate elevated
```

Inspect the audit log:

```bash
docker compose exec correlation-engine cat /data/alert_events.jsonl | python3 -m json.tool
```

---

## Production Alternatives

| Lab Tool | Production Alternative | Key Difference |
|---|---|---|
| Python `queue.Queue` | Apache Kafka | Persistent, distributed, replayable |
| In-process threads | Kafka consumer groups | Scalable across nodes |
| JSON Lines file | Elasticsearch / Loki | Indexed, queryable log store |
| `print()` notifier | PagerDuty / Slack API | Reliable delivery with acknowledgment |

The pattern—publish once, consume many—remains identical regardless of the transport.

---

## Experiment: Add a Fourth Subscriber

Add a **metrics exporter** that counts events by severity:

```python
from collections import Counter

severity_counts = Counter()

def metrics_exporter(event: dict):
    severity_counts[event.get("severity", "unknown")] += 1
    print(f"[METRICS] Severity counts: {dict(severity_counts)}")
```

Wire it into the bus:

```python
metrics_q = bus.subscribe()
bus.start_consumer("metrics-exporter", metrics_q, metrics_exporter)
```

Notice: **zero changes** to the publisher or other subscribers. This is the power of event-driven decoupling.

---

## Debrief

- What happens if Subscriber 2 (correlator) is slow? Does it block the publisher?
- What happens if a subscriber crashes? Are events lost?
- How does Kafka solve both problems? (Hint: consumer offsets and persistence.)
- In your environment, what event bus would you use?

In the next lesson, you will inject a full cascading failure and use every tool built in this module to trace it to its root cause.
