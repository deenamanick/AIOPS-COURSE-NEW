#!/usr/bin/env python3
"""remediation_report.py — Generate a weekly auto-remediation summary report.

Usage:
    python3 scripts/remediation_report.py --days 7
    python3 scripts/remediation_report.py --days 30 --url http://localhost:5001
"""

import argparse
import sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

LAB_URL = "http://localhost:5001"


def main():
    parser = argparse.ArgumentParser(description="Generate remediation report.")
    parser.add_argument("--days", type=int, default=7, help="Report period in days (default: 7)")
    parser.add_argument("--url", default=LAB_URL, help=f"Lab URL (default: {LAB_URL})")
    args = parser.parse_args()

    try:
        log = requests.get(f"{args.url}/api/remediation-log", timeout=10).json()
    except Exception as e:
        print(f"❌ Could not fetch remediation log: {e}")
        sys.exit(1)

    if not log:
        print("No remediation events found. Run some drills first.")
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)

    def in_window(entry):
        try:
            ts = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            return ts >= cutoff
        except Exception:
            return False

    entries = [e for e in log if in_window(e)]
    by_outcome = defaultdict(int)
    by_playbook = defaultdict(lambda: defaultdict(int))

    for e in entries:
        outcome = e.get("outcome", "unknown")
        playbook = e.get("playbook") or "flag-rollback"
        by_outcome[outcome] += 1
        by_playbook[playbook][outcome] += 1

    total = len(entries)
    success = by_outcome.get("metric-recovered", 0) + by_outcome.get("flags-disabled", 0)
    failed = by_outcome.get("playbook-error", 0) + by_outcome.get("verify-failed", 0)
    rolledback = by_outcome.get("rolled-back", 0)
    skipped = by_outcome.get("duplicate", 0) + by_outcome.get("rate-limit-hit", 0)
    resolved = by_outcome.get("alert-cleared", 0)

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%d")

    print("═" * 65)
    print(f"  Auto-Remediation Report — {start_date} to {end_date}")
    print("═" * 65)
    print(f"  Total events:      {total}")
    print(f"  Successful:        {success}  ({round(success/max(total,1)*100, 1)}%)")
    print(f"  Failed:            {failed}  ({round(failed/max(total,1)*100, 1)}%)")
    print(f"  Rolled back:       {rolledback}  ({round(rolledback/max(total,1)*100, 1)}%)")
    print(f"  Skipped (dedup):   {skipped}")
    print(f"  Alerts resolved:   {resolved}")
    print()
    print(f"  By playbook:")
    for playbook, outcomes in sorted(by_playbook.items()):
        pb_total = sum(outcomes.values())
        pb_success = outcomes.get("metric-recovered", 0) + outcomes.get("flags-disabled", 0)
        print(f"    {playbook:<30} {pb_total} runs  |  {pb_success} success")

    print("═" * 65)


if __name__ == "__main__":
    main()
