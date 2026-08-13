# 03 — SIEM Correlation & Insider Threat Detection

A Security Information and Event Management (SIEM) system does for security events exactly what Module 8's correlation engine did for infrastructure alerts: it groups related signals from different sources into a single, actionable incident rather than flooding an analyst with individual alerts.

---

## Why Individual Security Alerts Fail

Consider these three events, each from a different source:

```text
[Auth Service]     2026-08-11T02:03:14Z  bob  LOGIN_SUCCESS  ip=203.0.113.42
[File Audit]       2026-08-11T02:04:02Z  bob  READ  /opt/db/backups/prod_dump.sql.gz  (4.1 GB)
[Network Monitor]  2026-08-11T02:08:55Z  bob  EGRESS  dst=203.0.113.42  bytes=4312495821
```

Each event in isolation is ambiguous:
- A login success at 2 AM could be legitimate remote work.
- Reading a backup file could be a legitimate restore test.
- An outbound transfer could be a scheduled backup job.

**Correlated together**, with a 6-minute gap and the same destination IP, these three events form an unambiguous insider data exfiltration incident.

---

## SIEM Correlation Rules

A SIEM correlation rule defines a *pattern* across multiple events within a *time window*. When the pattern matches, the SIEM fires a single high-confidence incident alert.

### Rule Format Used in This Lab

```python
{
  "rule_id":     "INSIDER_EXFIL_001",
  "description": "Large data exfiltration following sensitive file access",
  "window_sec":  600,          # All events must occur within 10 minutes
  "conditions": [
    {"source": "auth",    "event": "LOGIN_SUCCESS"},
    {"source": "file",    "event": "READ",  "filter": {"path_contains": "/backups/"}},
    {"source": "network", "event": "EGRESS","filter": {"bytes_gt": 1_000_000_000}}
  ],
  "group_by":    "user",        # All events must share the same user
  "severity":    "CRITICAL",
  "response":    "page_security_oncall"
}
```

---

## Lab: SIEM Correlation Engine

### Step 1: Fetch Raw Security Events

```bash
python3 scripts/fetch_siem_events.py --output data/siem_events.json
```

This pulls the last 24 hours of events from all three sources (auth, file audit, network) from the lab app.

### Step 2: Run the Correlation Engine

```bash
python3 scripts/siem_correlator.py \
  --events data/siem_events.json \
  --output output/correlated_incidents.json
```

`scripts/siem_correlator.py`:

```python
#!/usr/bin/env python3
"""
Module 12 — SIEM Correlation Engine
Groups raw security events into correlated incidents using sliding-window rules.
"""

import json
from datetime import datetime, timezone
from collections import defaultdict

RULES = [
    {
        "rule_id": "INSIDER_EXFIL_001",
        "description": "Large data exfiltration following sensitive file access",
        "window_sec": 600,
        "conditions": [
            {"source": "auth",    "event_type": "LOGIN_SUCCESS"},
            {"source": "file",    "event_type": "READ",   "path_contains": "/backups/"},
            {"source": "network", "event_type": "EGRESS", "bytes_gt": 1_000_000_000},
        ],
        "group_by": "user",
        "severity": "CRITICAL",
    },
    {
        "rule_id": "BRUTE_FORCE_001",
        "description": "Brute force: 5+ failed logins followed by success",
        "window_sec": 300,
        "conditions": [
            {"source": "auth", "event_type": "LOGIN_FAILURE", "count_gte": 5},
            {"source": "auth", "event_type": "LOGIN_SUCCESS"},
        ],
        "group_by": "user",
        "severity": "HIGH",
    },
    {
        "rule_id": "CRED_ACCESS_001",
        "description": "Access to credential files outside business hours",
        "window_sec": 3600,
        "conditions": [
            {"source": "auth",  "event_type": "LOGIN_SUCCESS",   "hour_outside": (9, 18)},
            {"source": "file",  "event_type": "READ",            "path_contains": "/etc/"},
        ],
        "group_by": "user",
        "severity": "HIGH",
    },
]


def parse_time(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def match_condition(event: dict, condition: dict) -> bool:
    if event.get("source") != condition["source"]:
        return False
    if event.get("event_type") != condition["event_type"]:
        return False
    if "path_contains" in condition:
        if condition["path_contains"] not in event.get("path", ""):
            return False
    if "bytes_gt" in condition:
        if event.get("bytes", 0) <= condition["bytes_gt"]:
            return False
    if "hour_outside" in condition:
        start, end = condition["hour_outside"]
        hour = parse_time(event["timestamp"]).hour
        if start <= hour < end:  # Within business hours = not a match
            return False
    return True


def evaluate_rule(events: list[dict], rule: dict) -> list[dict]:
    """Find all groups of events that match the rule within the time window."""
    incidents = []
    by_group = defaultdict(list)
    for e in events:
        by_group[e.get(rule["group_by"], "unknown")].append(e)

    for group_val, group_events in by_group.items():
        group_events.sort(key=lambda e: e["timestamp"])
        # Sliding window
        for i, anchor in enumerate(group_events):
            window_events = [
                e for e in group_events
                if abs((parse_time(e["timestamp"]) - parse_time(anchor["timestamp"])).total_seconds())
                   <= rule["window_sec"]
            ]
            matched_conditions = []
            for condition in rule["conditions"]:
                count_needed = condition.get("count_gte", 1)
                matching = [e for e in window_events if match_condition(e, condition)]
                if len(matching) >= count_needed:
                    matched_conditions.append(condition)

            if len(matched_conditions) == len(rule["conditions"]):
                incident = {
                    "incident_id":  f"{rule['rule_id']}-{group_val}-{anchor['timestamp'][:10]}",
                    "rule_id":      rule["rule_id"],
                    "description":  rule["description"],
                    "severity":     rule["severity"],
                    "group_by":     rule["group_by"],
                    "group_value":  group_val,
                    "window_start": anchor["timestamp"],
                    "event_count":  len(window_events),
                    "matched_events": window_events[:10],  # Truncate for readability
                }
                # Deduplicate
                if not any(i["incident_id"] == incident["incident_id"] for i in incidents):
                    incidents.append(incident)
                break

    return incidents


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.events) as f:
        events = json.load(f)

    all_incidents = []
    for rule in RULES:
        found = evaluate_rule(events, rule)
        all_incidents.extend(found)
        for inc in found:
            print(f"🚨 [{inc['severity']:8s}] {inc['rule_id']}  "
                  f"user={inc['group_value']}  "
                  f"events={inc['event_count']}  "
                  f"start={inc['window_start']}")

    with open(args.output, "w") as f:
        json.dump(all_incidents, f, indent=2)

    print(f"\nCorrelated incidents: {len(all_incidents)}")
    print(f"Report written → {args.output}")


if __name__ == "__main__":
    main()
```

### Step 3: Review the Correlated Incidents

```bash
cat output/correlated_incidents.json | python3 -m json.tool | head -60
```

When the insider threat from Lesson 02 is active, you will see:

```text
🚨 [CRITICAL ] INSIDER_EXFIL_001  user=bob  events=3  start=2026-08-11T02:03:14Z
🚨 [HIGH     ] CRED_ACCESS_001   user=bob  events=2  start=2026-08-11T02:03:14Z

Correlated incidents: 2
```

A single session from `bob` triggered **two** correlation rules simultaneously — another signal that reinforces the confidence of the alert.

---

## Comparing Signal Counts: SIEM vs Raw Alerts

Without correlation, an analyst would receive 47+ individual events from `bob`'s session. With SIEM correlation, they receive **2 high-confidence incidents** with all evidence pre-assembled. This is the same multiplier you achieved with Module 8's infrastructure alert correlation.

| Approach | Analyst receives | Time to investigate |
|---|---|---|
| Raw event forwarding | 47 log lines | 45–90 minutes |
| Threshold alerts | 6 individual alerts | 20–30 minutes |
| **SIEM correlation** | **2 prioritised incidents** | **5–10 minutes** |

---

## Validation Checklist

- [ ] `siem_events.json` fetched with events from auth, file, and network sources.
- [ ] Correlation engine runs without errors and prints results to stdout.
- [ ] With insider threat active: `INSIDER_EXFIL_001` rule fires for `bob`.
- [ ] With insider threat active: `CRED_ACCESS_001` rule also fires.
- [ ] Without the insider threat: no `CRITICAL` incidents.
- [ ] You can explain why SIEM correlation reduces alert fatigue.
