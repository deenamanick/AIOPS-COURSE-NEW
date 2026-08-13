#!/usr/bin/env python3
"""
Collect live state data from the running Markov lab Flask app.

Polls the /api/state endpoint at regular intervals and writes
the results to a CSV file for offline analysis or matrix building.

Usage:
  python3 collect_live.py --duration 300 --output data/live_states.csv
  python3 collect_live.py --duration 60 --interval 5
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    sys.exit("❌ requests not installed. Run: pip install requests")

DEFAULT_URL = "http://localhost:5002/api/state"


def collect(url: str, duration: int, interval: int, output: str):
    """Poll the state API and save results to CSV."""
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    print(f"Collecting state data from {url}")
    print(f"  Duration:  {duration}s")
    print(f"  Interval:  {interval}s")
    print(f"  Output:    {output}")
    print(f"  Press Ctrl+C to stop early\n")

    fieldnames = ["timestamp", "state", "cpu", "mem", "disk", "error_rate", "p_failed"]
    rows = []
    start = time.time()

    try:
        while time.time() - start < duration:
            try:
                resp = requests.get(url, timeout=3)
                resp.raise_for_status()
                data = resp.json()

                row = {
                    "timestamp": data.get("timestamp",
                                          datetime.now(timezone.utc).isoformat()),
                    "state": data.get("state", "Unknown"),
                    "cpu": data.get("cpu", 0),
                    "mem": data.get("mem", 0),
                    "disk": data.get("disk", 0),
                    "error_rate": data.get("error_rate", 0),
                    "p_failed": data.get("p_failed", 0),
                }
                rows.append(row)

                elapsed = int(time.time() - start)
                print(f"  [{elapsed:3d}s] {row['state']:10s}  "
                      f"cpu={row['cpu']:5.1f}%  mem={row['mem']:5.1f}%  "
                      f"err={row['error_rate']:.3f}  P(F)={row['p_failed']:.3f}")

            except requests.RequestException as exc:
                elapsed = int(time.time() - start)
                print(f"  [{elapsed:3d}s] ❌ Request failed: {exc}")

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n  ⚠️ Collection stopped early by user.")

    # Write CSV
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n  ✅ {len(rows)} data points saved to {output}")


def main():
    parser = argparse.ArgumentParser(description="Collect live state data from the Markov lab app")
    parser.add_argument("--url", default=DEFAULT_URL,
                        help=f"State API URL (default: {DEFAULT_URL})")
    parser.add_argument("--duration", type=int, default=300,
                        help="Collection duration in seconds (default: 300)")
    parser.add_argument("--interval", type=int, default=10,
                        help="Polling interval in seconds (default: 10)")
    parser.add_argument("--output", default=os.path.join(
                            os.path.dirname(__file__), "..", "data", "live_states.csv"),
                        help="Output CSV path")
    args = parser.parse_args()

    collect(args.url, args.duration, args.interval, args.output)


if __name__ == "__main__":
    main()
