# Module 8: Log Analytics & Event Correlation

Welcome to Module 8! In Module 7, you turned observability signals into actionable alerts, defined SLOs, calculated error budgets, and reduced an alert storm to one root-cause notification. Alerting tells you **when** something is wrong; this module teaches you **why** it is wrong by correlating logs, alerts, and topology into a single incident with an identified root cause.

---

## Learning Objectives

By the end of this module, you will be able to:

1. Parse raw **Nginx access logs** into structured JSON using Python.
2. Enrich log entries with contextual fields such as hostname, service name, and trace ID.
3. Correlate multiple alerts within a **time window** and group them into a single incident.
4. Build a **dependency graph** and use topology-based reasoning to separate root cause from symptoms.
5. Implement a simple **event-driven pub/sub** architecture that decouples producers from consumers.
6. Trace a **cascading failure** from disk pressure through connection-pool exhaustion to user-facing 5xx errors.

---

## Prerequisites

- ✅ Module 7 completed
- ✅ Docker Engine and Docker Compose v2 installed
- ✅ Python 3.10+ available on the host
- ✅ Familiarity with JSON, basic Python, and PromQL
- ✅ `curl` and a browser available
- ✅ At least 4 GB RAM available

---

## Lab Architecture

```text
Nginx ─── access.log ──► Log Parser ──► Structured JSON
                                              │
                                    ┌─────────┴──────────┐
                                    ▼                    ▼
                             Analytics Engine     Enrichment Layer
                            (top-10, error rate)  (hostname, trace_id)

Alert Stream ──► Pub/Sub Bus ──► Correlation Engine ──► Incident
                     │                    │
                     ├── File Logger       └── Dependency Graph
                     └── Notifier               (User → App → DB)
```

The lab runs a multi-service stack (Nginx → Flask → Postgres-simulator) that generates realistic logs and cascading failures. A Python correlation engine groups co-occurring alerts and walks the dependency graph to identify the root cause.

---

## Lab Setup

```bash
cd Module-8/lab
docker compose up -d --build
docker compose ps
```

Open:

- Nginx reverse proxy: `http://localhost:8080`
- Flask service: `http://localhost:5000` (internal)
- Log viewer: `docker compose logs -f nginx`
- Correlation engine output: `docker compose logs -f correlation-engine`

---

## Lessons in this Module

| # | Lesson | What You'll Do |
|---|---|---|
| 01 | [Structured vs Unstructured Logging](./01-structured-vs-unstructured-logging.md) | Compare plain-text and JSON logging, understand why structure matters |
| 02 | [Log Parsing & Enrichment](./02-log-parsing-enrichment.md) | Parse raw Nginx logs into structured JSON and enrich with context |
| 03 | [Time-Window Alert Correlation](./03-time-window-correlation.md) | Group co-occurring alerts into a single incident using time windows |
| 04 | [Dependency Graphs & Root Cause Analysis](./04-dependency-graph-rca.md) | Build a topology map and walk it to separate root cause from symptoms |
| 05 | [Event-Driven Architecture Lab](./05-event-driven-pubsub.md) | Implement a pub/sub system with file logger, correlator, and notifier |
| 06 | [Break/Fix: Cascading Failure](./06-break-fix-cascade.md) | Inject a disk-full failure, trace the cascade, and identify root cause |

Start with **01-structured-vs-unstructured-logging.md**.
