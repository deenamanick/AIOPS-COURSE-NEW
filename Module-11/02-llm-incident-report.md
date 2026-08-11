# 02 — LLM Incident Report Lab

The LLM's most immediately useful AIOps capability is **structured incident report generation**. Given a set of correlated alerts, relevant log lines, and anomaly detection results, the LLM synthesises a Root Cause Analysis (RCA) report in seconds — a task that normally takes a senior engineer 30–60 minutes of log trawling and timeline reconstruction.

This lesson teaches you to build the prompt, call the local LLM, and produce a structured RCA report that a human can validate and act on.

---

## The Problem with Unstructured Incident Data

At the moment an alert fires, your incident data is scattered across multiple systems:

```text
Alertmanager:   [FIRING] DiskAlmostFull on db-server-01 — 87.3%
Prometheus:     sim_disk_usage_pct{instance="db-server-01"} = 87.3
App logs:       ERROR  db connection timeout after 30s
App logs:       ERROR  write failed: no space left on device
App logs:       WARN   slow query: SELECT * FROM events took 12.3s
Module 5 score: Anomaly score = 94.2 (threshold: 70) — CRITICAL
Module 9 forecast: Disk 100% in 1h 42m at current growth rate
```

A human engineer must mentally correlate this into a timeline, identify the root cause, and decide what to do. The LLM does this in under 5 seconds.

---

## The Prompt Engineering Formula

A good incident analysis prompt has five sections:

```text
[ROLE]       You are an expert Site Reliability Engineer...
[CONTEXT]    Here is the incident data: alerts, logs, anomaly scores...
[TASK]       Generate a Root Cause Analysis report with the following sections...
[FORMAT]     Use Markdown. Each section must be present even if brief.
[CONSTRAINT] Base your analysis only on the data provided. Do not invent metrics.
```

The constraint is the most important element — it reduces hallucination by anchoring the LLM to the evidence you provide.

---

## Step 1: Gather the Incident Context

The lab script `scripts/build_prompt.py` collects data from all the lab endpoints and assembles it into a structured prompt:

```bash
cd Module-11/lab
python3 scripts/build_prompt.py --output prompts/incident_context.txt
```

This queries:
- `http://localhost:5002/api/incident-context` — current alerts, metrics, anomaly score
- `http://localhost:5002/api/logs` — the last 20 log lines
- `http://localhost:5002/api/forecast` — disk forecast from the Module-9-style engine

Inspect the assembled prompt:

```bash
cat prompts/incident_context.txt
```

```text
=== INCIDENT CONTEXT ===
Timestamp: 2026-08-11T06:45:00Z
Environment: training

=== ACTIVE ALERTS ===
[FIRING] DiskAlmostFull | severity=warning | disk=87.3% | instance=db-server-01
[FIRING] AppSlowResponse | severity=warning | p99_latency=4200ms | threshold=500ms
[FIRING] DBConnectionErrors | severity=critical | error_rate=23% | instance=db-server-01

=== ANOMALY SCORES (Module 5) ===
Disk usage anomaly score:  94.2 / 100  (CRITICAL — threshold: 70)
Error rate anomaly score:  78.1 / 100  (HIGH)
Latency anomaly score:     61.3 / 100  (ELEVATED)

=== FORECAST (Module 9) ===
Disk will reach 100% in approximately 1h 42m at current growth rate (+8.3%/hr)

=== RECENT LOGS (last 20 lines) ===
2026-08-11T06:44:10Z ERROR  [db-server-01] write failed: no space left on device
2026-08-11T06:44:08Z ERROR  [app-server-01] db connection timeout after 30s
2026-08-11T06:44:05Z WARN   [app-server-01] slow query: SELECT * FROM events took 12.3s
2026-08-11T06:43:55Z ERROR  [db-server-01] write failed: no space left on device
2026-08-11T06:43:50Z INFO   [app-server-01] request /api/checkout failed with 503
2026-08-11T06:43:40Z ERROR  [db-server-01] WAL archive log rotation failed — disk full
...
```

---

## Step 2: Build and Send the Full Prompt

```bash
python3 scripts/generate_rca.py \
  --context prompts/incident_context.txt \
  --model llama3.2:3b \
  --output output/rca_report.md
```

The prompt sent to Ollama:

```text
You are an expert Site Reliability Engineer specialising in root cause analysis
and incident investigation. Your task is to analyse the incident data below and
produce a structured Root Cause Analysis (RCA) report.

INCIDENT DATA:
---
[full content of incident_context.txt]
---

Generate a Root Cause Analysis report with EXACTLY these sections:

## Summary
One-sentence description of the incident and its user impact.

## Timeline
Bullet list of events in chronological order based on the log timestamps.

## Root Cause
The single most likely root cause, supported by evidence from the data.

## Contributing Factors
Secondary factors that made the incident worse or harder to detect.

## Affected Services
List every service impacted and describe how it was affected.

## Recommended Immediate Fix
The specific action that will resolve the incident right now.
Suggest Ansible playbooks or specific commands where appropriate.

## Prevention Steps
Three concrete changes that would prevent this class of incident in future.

BASE YOUR ANALYSIS ONLY ON THE DATA PROVIDED. Do not invent metrics or events
not present in the data above. If evidence is insufficient for a section,
state "Insufficient data" rather than guessing.
```

---

## Step 3: Review the Generated RCA

After ~10 seconds, `output/rca_report.md` is written:

```markdown
## Summary

A disk space exhaustion on `db-server-01` caused write failures in the
PostgreSQL WAL archive, leading to database connection timeouts and a 23%
error rate on the application tier, degrading the checkout API for all users.

## Timeline

- **06:43:40Z** — WAL archive log rotation failed due to disk full condition
- **06:43:50Z** — App requests to `/api/checkout` began returning 503
- **06:43:55Z** — First `write failed: no space left on device` errors logged
- **06:44:05Z** — Slow queries detected (12.3s vs normal <100ms)
- **06:44:08Z** — DB connection timeouts began appearing on app-server-01
- **06:44:10Z** — Alerts firing: DiskAlmostFull, AppSlowResponse, DBConnectionErrors
- **06:45:00Z** — Anomaly detection scores CRITICAL on disk (94.2/100)

## Root Cause

Disk usage on `db-server-01` grew to 87.3% due to unrotated WAL (Write-Ahead
Log) archive files. When the filesystem reached capacity, PostgreSQL could no
longer write WAL entries, blocking all write transactions. This cascaded to
the application tier as connection timeouts and 503 errors.

**Evidence**: "WAL archive log rotation failed — disk full" log at 06:43:40Z
preceded all application-layer errors by 10–18 seconds.

## Contributing Factors

- Log rotation policy was not enforcing a maximum WAL archive size
- No predictive alert was configured for WAL archive growth specifically
- The 30-second DB connection timeout is too long; it held connections
  open during degradation, exhausting the pool faster

## Affected Services

| Service | Impact |
|---|---|
| PostgreSQL (db-server-01) | WAL writes blocked; all write transactions failed |
| app-server-01 | 503 errors on all write endpoints; connection pool exhausted |
| /api/checkout | 100% failure rate during the incident window |

## Recommended Immediate Fix

Run the `clear-logs.yml` Ansible playbook (Module 10) targeting the WAL
archive directory:

```bash
ansible-playbook -i playbooks/inventory.ini playbooks/clear-logs.yml \
  -e log_dir=/var/lib/postgresql/wal_archive -e max_age_days=3
```

This will delete WAL archive files older than 3 days, recovering approximately
4–6 GB of disk space and allowing PostgreSQL to resume normal operation.

## Prevention Steps

1. **Configure WAL archive retention policy**: Set `archive_cleanup_command`
   in `postgresql.conf` to remove WAL files older than 7 days automatically.

2. **Add a specific WAL disk alert**: Create a Prometheus alert for
   WAL archive directory size, separate from the general disk alert,
   with a lower threshold (70%) and a shorter firing window (1 minute).

3. **Implement predictive capacity alerts**: The Module 9 forecast shows
   disk hitting 100% in 1h 42m. A predictive alert should fire at the
   2-hour-remaining mark to provide remediation lead time.
```

---

## Evaluating LLM Output Quality

After reviewing the report, score it on these criteria:

| Criterion | Check |
|---|---|
| **Accuracy** | Is the root cause consistent with the actual log evidence? |
| **Completeness** | Are all affected services listed? Is the timeline complete? |
| **Actionability** | Is the recommended fix specific and executable? |
| **Hallucination check** | Does the report invent any metric values or events not in the data? |
| **Causality** | Does the timeline show cause → effect correctly? |

For `llama3.2:3b`, expect 80–90% accuracy on structured incident data. `mistral:7b` typically scores 90–95%. Never publish an LLM-generated RCA without a human review.

---

## Comparing Local vs Cloud Output

Run the same prompt against the OpenAI API if you have access:

```bash
python3 scripts/generate_rca.py \
  --context prompts/incident_context.txt \
  --model gpt-4o \
  --openai \
  --output output/rca_gpt4o.md
```

Then diff the two reports:

```bash
diff output/rca_report.md output/rca_gpt4o.md
```

Compare:
- Which report identified the root cause more precisely?
- Which prevention steps were more specific?
- Did either model hallucinate any data?
- Was the quality difference worth the cloud cost and privacy trade-off?

---

## Validation Checklist

- [ ] `build_prompt.py` assembled the incident context from all three data sources.
- [ ] `generate_rca.py` called Ollama and produced `output/rca_report.md`.
- [ ] The root cause in the report matches the WAL archive disk exhaustion.
- [ ] The timeline is in chronological order with no invented events.
- [ ] The recommended fix references the `clear-logs.yml` Ansible playbook.
- [ ] LLM output was reviewed and scored on all five quality criteria.
