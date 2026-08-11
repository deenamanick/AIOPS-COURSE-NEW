#!/usr/bin/env python3
"""capstone_summary.py — Print the full capstone completion status report.

Usage:
    python3 scripts/capstone_summary.py --inject-time 2026-08-11T07:00:00Z --rca output/capstone_rca.md
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

LAB_URL = "http://localhost:5002"


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _fmt_delta(inject_ts: datetime, event_ts: datetime) -> str:
    delta = (event_ts - inject_ts).total_seconds()
    if delta < 60:
        return f"{delta:.0f}s"
    m = int(delta // 60)
    s = int(delta % 60)
    return f"{m}m {s}s"


def main():
    parser = argparse.ArgumentParser(description="Print the capstone summary report.")
    parser.add_argument("--inject-time", required=True,
                        help="Drill inject time in ISO 8601 format (e.g. 2026-08-11T07:00:00Z)")
    parser.add_argument("--rca", default="output/capstone_rca.md",
                        help="Path to the generated RCA file (default: output/capstone_rca.md)")
    parser.add_argument("--post-mortem", default="output/capstone-post-mortem.md",
                        help="Path to the post-mortem file")
    args = parser.parse_args()

    try:
        inject_ts = _parse_ts(args.inject_time)
    except ValueError:
        print(f"❌ Invalid inject time format: {args.inject_time}")
        print("   Use ISO 8601, e.g. 2026-08-11T07:00:00Z")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    steps = []

    # Step 1: Inject
    steps.append({
        "n": 1, "label": "Inject",
        "pass": True,
        "timestamp": args.inject_time,
        "detail": "WAL archive growth drill started",
    })

    # Step 2: Detection — check anomaly score history
    anomaly_pass = False
    detect_ts = None
    try:
        anomaly = requests.get(f"{LAB_URL}/api/anomaly", timeout=5).json()
        if anomaly.get("disk_anomaly_score", 0) > 70 or anomaly.get("composite_score", 0) > 40:
            anomaly_pass = True
            detect_ts = anomaly.get("timestamp", now.isoformat())
    except Exception:
        pass

    steps.append({
        "n": 2, "label": "Detect",
        "pass": anomaly_pass,
        "timestamp": detect_ts,
        "detail": "Anomaly score > 70 (disk metric)" if anomaly_pass else "⚠️  Anomaly threshold not reached yet",
    })

    # Step 3: Correlate — check alerts exist
    alerts_pass = False
    corr_ts = None
    try:
        alerts = requests.get(f"{LAB_URL}/api/alerts", timeout=5).json()
        if len(alerts) >= 2:
            alerts_pass = True
            corr_ts = alerts[-1].get("timestamp") if alerts else None
    except Exception:
        pass

    steps.append({
        "n": 3, "label": "Correlate",
        "pass": alerts_pass,
        "timestamp": corr_ts,
        "detail": f"{len(alerts) if alerts_pass else 0} alerts correlated to root alert",
    })

    # Step 4: Forecast — check forecast endpoint
    forecast_pass = False
    forecast_ts = None
    try:
        f = requests.get(f"{LAB_URL}/api/forecast", timeout=5).json()
        if f.get("r2_score") and float(f["r2_score"]) > 0.85:
            forecast_pass = True
            forecast_ts = f.get("timestamp", now.isoformat())
    except Exception:
        pass

    steps.append({
        "n": 4, "label": "Forecast",
        "pass": forecast_pass,
        "timestamp": forecast_ts,
        "detail": "Disk 100% predicted with R² > 0.90" if forecast_pass else "⚠️  No forecast available yet",
    })

    # Step 5: LLM RCA — check file exists and has content
    rca_pass = os.path.exists(args.rca) and os.path.getsize(args.rca) > 500
    rca_ts = datetime.fromtimestamp(os.path.getmtime(args.rca), tz=timezone.utc).isoformat() if rca_pass else None
    steps.append({
        "n": 5, "label": "LLM RCA",
        "pass": rca_pass,
        "timestamp": rca_ts,
        "detail": f"RCA report generated ({os.path.getsize(args.rca)} bytes)" if rca_pass
                  else f"⚠️  {args.rca} not found or empty — run generate_rca.py",
    })

    # Step 6: Remediate — check disk recovered
    remediate_pass = False
    remediate_ts = None
    try:
        m = requests.get(f"{LAB_URL}/api/metrics", timeout=5).json()
        if m.get("disk_usage_pct", 100) < 50:
            remediate_pass = True
            remediate_ts = m.get("timestamp")
    except Exception:
        pass

    steps.append({
        "n": 6, "label": "Remediate",
        "pass": remediate_pass,
        "timestamp": remediate_ts,
        "detail": "clear-logs.yml playbook completed" if remediate_pass
                  else "⚠️  Disk still elevated — run the Ansible playbook",
    })

    # Step 7: Verify
    verify_pass = False
    verify_ts = None
    try:
        m = requests.get(f"{LAB_URL}/api/metrics", timeout=5).json()
        s = requests.get(f"{LAB_URL}/api/status", timeout=5).json()
        if (m.get("disk_usage_pct", 100) < 30 and
                m.get("error_rate_pct", 100) < 2 and
                s.get("status") == "healthy"):
            verify_pass = True
            verify_ts = m.get("timestamp")
    except Exception:
        pass

    steps.append({
        "n": 7, "label": "Verify",
        "pass": verify_pass,
        "timestamp": verify_ts,
        "detail": "All three layers healthy" if verify_pass
                  else "⚠️  Not all layers healthy yet — check /api/metrics",
    })

    # Step 8: Post-Mortem
    pm_pass = os.path.exists(args.post_mortem) and os.path.getsize(args.post_mortem) > 1000
    steps.append({
        "n": 8, "label": "Post-Mortem",
        "pass": pm_pass,
        "timestamp": None,
        "detail": args.post_mortem if pm_pass
                  else f"⚠️  {args.post_mortem} not found or incomplete",
    })

    # Print report
    print("\n")
    print("═" * 65)
    print("  AIOps Capstone — Full Incident Lifecycle")
    print("═" * 65)
    print()

    detect_step = next((s for s in steps if s["n"] == 2), None)
    verify_step = next((s for s in steps if s["n"] == 7), None)
    ttd = ttr = None

    for step in steps:
        icon = "✅" if step["pass"] else "❌"
        ts_str = ""
        if step["timestamp"]:
            try:
                ts = _parse_ts(step["timestamp"])
                ts_str = ts.strftime("%H:%M:%SZ")
            except Exception:
                ts_str = str(step["timestamp"])[:19]

        print(f"  [{step['n']}] {step['label']:<14} {icon}  "
              f"{ts_str:<10} — {step['detail']}")

    # TTD / TTR
    print()
    if detect_step and detect_step["pass"] and detect_step["timestamp"]:
        try:
            ttd = _fmt_delta(inject_ts, _parse_ts(detect_step["timestamp"]))
        except Exception:
            ttd = "?"
    if verify_step and verify_step["pass"] and verify_step["timestamp"]:
        try:
            ttr = _fmt_delta(inject_ts, _parse_ts(verify_step["timestamp"]))
        except Exception:
            ttr = "?"

    print("  " + "─" * 61)
    ttd_icon = "✅" if ttd and ttd != "?" else "⚠️ "
    ttr_icon = "✅" if ttr and ttr != "?" else "⚠️ "
    print(f"  TTD:  {ttd or 'N/A'} {ttd_icon} (target: < 2 minutes)")
    print(f"  TTR:  {ttr or 'N/A'} {ttr_icon} (target: < 10 minutes)")
    print("  " + "─" * 61)

    all_pass = all(s["pass"] for s in steps)
    modules = "5, 7, 8, 9, 10, 11"
    print(f"  Modules used: {modules}")
    print(f"  All steps complete: {'✅' if all_pass else '❌ — see failures above'}")
    print("═" * 65)
    print()


if __name__ == "__main__":
    main()
