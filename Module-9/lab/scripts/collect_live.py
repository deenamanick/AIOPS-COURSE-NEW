#!/usr/bin/env python3
"""
Live Metric Collector — Module 9

Polls the Flask app's /api/metrics endpoint at regular intervals
and writes data points to a CSV file for forecasting.

Usage:
  python3 collect_live.py --duration 180 --output data/live_disk.csv
"""

import argparse
import csv
import os
import sys
import time
import urllib.request
import json


def main():
    parser = argparse.ArgumentParser(description="Collect live metrics from the lab app")
    parser.add_argument("--duration", type=int, default=180,
                        help="Collection duration in seconds (default: 180)")
    parser.add_argument("--interval", type=int, default=10,
                        help="Polling interval in seconds (default: 10)")
    parser.add_argument("--url", default="http://localhost:5000/api/metrics",
                        help="Metrics endpoint URL")
    parser.add_argument("--output", default="data/live_disk.csv",
                        help="Output CSV file path")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    print(f"Collecting metrics for {args.duration}s (every {args.interval}s)...")
    print(f"Endpoint: {args.url}")
    print(f"Output: {args.output}\n")

    rows = []
    start = time.time()
    count = 0

    while (time.time() - start) < args.duration:
        try:
            with urllib.request.urlopen(args.url, timeout=5) as resp:
                data = json.loads(resp.read())
                row = {
                    "date": data["timestamp"].split("T")[0] if "T" in data["timestamp"]
                           else data["timestamp"][:10],
                    "value": data["disk_usage_pct"],
                }
                rows.append(row)
                count += 1
                print(f"  [{count:>3}] disk={data['disk_usage_pct']:.1f}%  "
                      f"cpu={data['cpu_usage_pct']:.1f}%  "
                      f"mem={data['memory_usage_pct']:.1f}%  "
                      f"err={data['error_rate_pct']:.2f}%")
        except Exception as e:
            print(f"  ⚠️  Failed to fetch: {e}")

        time.sleep(args.interval)

    # Write CSV
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "value"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ Collected {len(rows)} data points → {args.output}")


if __name__ == "__main__":
    main()
