#!/usr/bin/env python3
"""analyze_chaos.py — Analyze a traffic log from a chaos experiment and report TTD and TTR.

Usage:
    python3 scripts/analyze_chaos.py --log traffic.log --inject-time 2026-08-11T06:30:00Z
    python3 scripts/analyze_chaos.py --log traffic.log --inject-time 2026-08-11T06:30:00Z --experiment "Process Kill"
"""

import argparse
import json
from datetime import datetime, timezone


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def analyze(log_file: str, inject_time_str: str, experiment: str) -> dict:
    inject_time = parse_iso(inject_time_str)

    entries = []
    with open(log_file) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    if not entries:
        return {"error": "No entries in log file"}

    # Find the first failure after inject
    first_failure_ts = None
    last_failure_ts = None
    first_recovery_ts = None
    total = len(entries)
    failed_in_window = 0
    peak_error_rate = 0.0

    for entry in entries:
        ts = parse_iso(entry["timestamp"])
        if ts < inject_time:
            continue
        if not entry["ok"]:
            if first_failure_ts is None:
                first_failure_ts = ts
            last_failure_ts = ts
            failed_in_window += 1
        elif first_failure_ts is not None and first_recovery_ts is None:
            first_recovery_ts = ts

    total_after_inject = sum(1 for e in entries if parse_iso(e["timestamp"]) >= inject_time)
    if total_after_inject > 0:
        peak_error_rate = round(failed_in_window / total_after_inject * 100, 1)

    ttd_sec = None
    ttr_sec = None

    if first_failure_ts:
        ttd_sec = round((first_failure_ts - inject_time).total_seconds(), 1)
    if first_recovery_ts and inject_time:
        ttr_sec = round((first_recovery_ts - inject_time).total_seconds(), 1)

    return {
        "experiment": experiment,
        "inject_time": inject_time_str,
        "first_failure": first_failure_ts.isoformat() if first_failure_ts else "none",
        "first_recovery": first_recovery_ts.isoformat() if first_recovery_ts else "still-degraded",
        "ttd_seconds": ttd_sec,
        "ttr_seconds": ttr_sec,
        "failed_requests": failed_in_window,
        "total_requests_after_inject": total_after_inject,
        "peak_error_rate_pct": peak_error_rate,
        "ttd_pass": ttd_sec is not None and ttd_sec <= 120,
        "ttr_pass": ttr_sec is not None and ttr_sec <= 300,
    }


def _fmt(seconds) -> str:
    if seconds is None:
        return "N/A"
    if seconds < 60:
        return f"{seconds}s"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s}s"


def main():
    parser = argparse.ArgumentParser(description="Analyze chaos experiment results.")
    parser.add_argument("--log", required=True, help="Path to traffic log file")
    parser.add_argument("--inject-time", required=True, help="Inject time in ISO 8601 format")
    parser.add_argument("--experiment", default="Chaos Experiment",
                        help="Human-readable experiment name")
    args = parser.parse_args()

    result = analyze(args.log, args.inject_time, args.experiment)

    print("═" * 65)
    print(f"  Chaos Experiment: {result['experiment']}")
    print("═" * 65)

    if "error" in result:
        print(f"  ❌ Error: {result['error']}")
        return

    ttd_icon = "✅" if result.get("ttd_pass") else "❌"
    ttr_icon = "✅" if result.get("ttr_pass") else "❌"

    print(f"  Inject time:     {result['inject_time']}")
    print(f"  First failure:   {result['first_failure']}")
    print(f"  First recovery:  {result['first_recovery']}")
    print(f"  TTD:             {_fmt(result['ttd_seconds'])} {ttd_icon} (target: < 2 minutes)")
    print(f"  TTR:             {_fmt(result['ttr_seconds'])} {ttr_icon} (target: < 5 minutes)")
    print(f"  Failed requests: {result['failed_requests']} of {result['total_requests_after_inject']}")
    print(f"  Peak error rate: {result['peak_error_rate_pct']}%")

    overall = result.get("ttd_pass") and result.get("ttr_pass")
    print("─" * 65)
    print(f"  Overall: {'✅ PASS' if overall else '❌ FAIL — Review TTD/TTR targets'}")
    print("═" * 65)


if __name__ == "__main__":
    main()
