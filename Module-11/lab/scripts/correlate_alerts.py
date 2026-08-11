#!/usr/bin/env python3
"""correlate_alerts.py — Identify the root alert and correlate cascading alerts from the lab.

Usage:
    python3 scripts/correlate_alerts.py
    python3 scripts/correlate_alerts.py --url http://localhost:5002
"""

import argparse
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

LAB_URL = "http://localhost:5002"

# Alert cascade knowledge base: known secondary alerts triggered by each root cause
CASCADE_MAP = {
    "DiskAlmostFull": {
        "likely_cascade": ["DBConnectionErrors", "AppSlowResponse", "HighErrorRate"],
        "mechanism": "Disk full → WAL write fail → DB timeout → App 5xx",
    },
    "NginxDown": {
        "likely_cascade": ["HighErrorRate", "AppSlowResponse"],
        "mechanism": "Process down → no responses → error rate spikes → latency reports timeout",
    },
    "HighCPULoad": {
        "likely_cascade": ["AppSlowResponse"],
        "mechanism": "CPU saturation → slow request processing → p99 latency increases",
    },
}


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def correlate(alerts: list) -> dict:
    if not alerts:
        return {"root_alert": None, "correlated": [], "cascade": "No alerts firing"}

    # Sort by timestamp ascending
    sorted_alerts = sorted(alerts, key=lambda a: a.get("timestamp", ""))
    first = sorted_alerts[0]
    root_name = first.get("alertname", "Unknown")

    cascade_info = CASCADE_MAP.get(root_name, {})
    correlated = []

    root_ts = _parse_ts(first.get("timestamp", datetime.now(timezone.utc).isoformat()))
    for a in sorted_alerts[1:]:
        a_ts = _parse_ts(a.get("timestamp", root_ts.isoformat()))
        delta = round((a_ts - root_ts).total_seconds(), 0)
        correlated.append({
            "alertname": a.get("alertname"),
            "seconds_after_root": delta,
            "expected": a.get("alertname") in cascade_info.get("likely_cascade", []),
        })

    return {
        "root_alert": {
            "alertname": root_name,
            "severity": first.get("severity"),
            "value": first.get("value"),
            "unit": first.get("unit"),
            "timestamp": first.get("timestamp"),
        },
        "correlated": correlated,
        "cascade_mechanism": cascade_info.get("mechanism", "Unknown cascade pattern"),
        "total_alerts": len(sorted_alerts),
    }


def main():
    parser = argparse.ArgumentParser(description="Correlate alerts to identify the root cause.")
    parser.add_argument("--url", default=LAB_URL, help=f"Lab URL (default: {LAB_URL})")
    args = parser.parse_args()

    try:
        alerts = requests.get(f"{args.url}/api/alerts", timeout=10).json()
    except Exception as e:
        print(f"❌ Could not fetch alerts: {e}")
        sys.exit(1)

    if not alerts:
        print("No active alerts. Run a drill first:")
        print(f"  curl -X POST {args.url}/drill/wal-growth")
        return

    result = correlate(alerts)
    root = result["root_alert"]

    print("═" * 65)
    print("  Alert Correlation Analysis")
    print("═" * 65)

    if root:
        ts = root["timestamp"][:19].replace("T", " ") if root["timestamp"] else "?"
        print(f"  Root alert:  {root['alertname']} ({root['severity']}) "
              f"— fired at {ts}Z")
        print(f"  Value:       {root['value']}{root.get('unit', '')}")
        print()
        for c in result["correlated"]:
            icon = "✅" if c["expected"] else "⚠️ "
            print(f"  Correlated:  {c['alertname']:<28} (+{c['seconds_after_root']}s) {icon}")
        print()
        print(f"  Cascade:     {result['cascade_mechanism']}")

    print("─" * 65)
    print(f"  Total alerts: {result['total_alerts']}")
    print("═" * 65)


if __name__ == "__main__":
    main()
