# Post-Mortem: [INCIDENT TITLE — e.g. Disk Exhaustion on db-server-01]

**Date**: YYYY-MM-DD
**Authors**: [Your name]
**Severity**: SEV-1 / SEV-2 / SEV-3
**Status**: In Review

---

## Impact Summary

- **Duration**: HH:MM (from first symptom to full recovery)
- **User impact**: [What did users experience? Be specific — e.g. "All write operations to /api/checkout returned 503 for 24 minutes"]
- **Services affected**: [List each service]
- **SLO impact**: [Did the error budget burn? By how much?]

---

## Timeline

| Time (UTC) | Event |
|---|---|
| HH:MM:SS | [First log error or symptom] |
| HH:MM:SS | [First alert fired] |
| HH:MM:SS | [On-call paged / notified] |
| HH:MM:SS | [Root cause identified] |
| HH:MM:SS | [Fix applied] |
| HH:MM:SS | [Service recovering] |
| HH:MM:SS | [All-clear declared] |

*Add or remove rows as needed. Minimum 6 events.*

---

## Root Cause

[Single root cause — the deepest "Why" from your 5 Whys analysis. One sentence maximum.
Example: "Log rotation policy did not cover the WAL archive directory at /var/lib/postgresql/wal_archive."]

### 5 Whys Analysis

- **Symptom**: [The surface-level failure users experienced]
- **Why 1**: [Because...]
- **Why 2**: [Because...]
- **Why 3**: [Because...]
- **Why 4**: [Because...]
- **Why 5 / Root Cause**: [Because... — this is your root cause]

---

## Contributing Factors

- [Factor 1 — e.g. "No predictive alert was configured for the WAL archive directory specifically"]
- [Factor 2 — e.g. "DB connection timeout was 30s, exhausting the pool faster during degradation"]
- [Factor 3 — optional]

*Frame as system failures, not individual failures. Avoid "engineer forgot to..." — reframe as "no process existed to ensure..."*

---

## What Went Well

- [e.g. "Anomaly detection fired within 90 seconds of threshold breach"]
- [e.g. "Auto-remediation playbook ran and disk recovered without manual intervention"]
- [e.g. "LLM-generated RCA was accurate and saved ~20 minutes of log analysis"]

*Do not skip this section. It reinforces what works and improves morale.*

---

## What Went Wrong

- [e.g. "No dedicated alert for WAL archive directory — only the general disk alert"]
- [e.g. "Log rotation configuration was last reviewed 8 months ago"]
- [e.g. "First responder spent 3 minutes checking the wrong service before identifying db-server-01"]

---

## Where We Got Lucky

- [e.g. "The failure happened at 07:00 UTC, not during peak traffic at 14:00 UTC — user impact was 10x smaller"]
- [e.g. "Auto-scaling was not triggered — a second failure during the incident would have exhausted replicas"]

---

## Action Items

| Action | Owner | Due Date | Priority |
|---|---|---|---|
| Configure WAL archive retention policy in postgresql.conf | [Name] | YYYY-MM-DD | P1 |
| Add dedicated alert for WAL archive directory disk usage | [Name] | YYYY-MM-DD | P1 |
| Reduce DB connection timeout from 30s to 5s | [Name] | YYYY-MM-DD | P2 |
| Run game day for DB disk-full scenario | [Name] | YYYY-MM-DD | P2 |

*Every action item must have an owner (a person, not a team) and a due date. Add or remove rows.*

---

## Lessons Learned

[2–3 sentences summarising the systemic insight from this incident. What is the single most important thing your team now understands that you did not understand before?]

---

*Post-mortem written within 24 hours of the incident. Reviewed by: [name]. Published: YYYY-MM-DD.*
