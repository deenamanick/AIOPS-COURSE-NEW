#!/usr/bin/env python3
"""
Generate 30 days of simulated infrastructure metrics and map them to
discrete operational states for Markov chain analysis.

Outputs:
  data/raw_metrics.csv  — continuous metrics (720 rows, one per hour)
  data/state_log.csv    — same data with a 'state' column appended

Usage:
  python3 generate_state_data.py                  # Generate data
  python3 generate_state_data.py --stats           # Generate + print distribution
  python3 generate_state_data.py --days 60         # 60 days of data
"""

import argparse
import csv
import os
import random
from datetime import datetime, timedelta

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

STATES = ["Healthy", "Degraded", "Critical", "Failed"]


def map_state(cpu, mem, disk, error_rate):
    """Map continuous metrics to a discrete operational state."""
    if error_rate > 0.50:
        return "Failed"
    if cpu > 80 or mem > 80 or disk > 90:
        return "Critical"
    if cpu > 60 or mem > 60 or disk > 75:
        return "Degraded"
    return "Healthy"


def generate_metrics(days=30, points_per_day=24):
    """Generate realistic infrastructure metrics with natural patterns."""
    data = []
    base_date = datetime(2026, 7, 1)

    base_cpu = 30.0
    base_mem = 42.0
    base_disk = 35.0
    base_err = 0.02

    for i in range(days * points_per_day):
        hour = i % 24
        day = i // 24
        timestamp = base_date + timedelta(hours=i)

        # Daily pattern: higher during business hours (9-17)
        business_boost = 15 if 9 <= hour <= 17 else 0
        weekend_reduction = -10 if (base_date + timedelta(days=day)).weekday() >= 5 else 0

        cpu = base_cpu + business_boost + weekend_reduction + random.gauss(0, 8)
        mem = base_mem + (business_boost * 0.5) + random.gauss(0, 5)
        disk = base_disk + (day * 0.1) + random.gauss(0, 1)  # slow disk growth
        error_rate = base_err + random.gauss(0, 0.01)

        # Inject periodic degradation events (~every 5 days, during business hours)
        if day % 5 == 0 and 10 <= hour <= 14:
            cpu += 30 + random.uniform(0, 10)
            mem += 20 + random.uniform(0, 5)
            error_rate += 0.05 + random.uniform(0, 0.03)

        # Inject a critical incident window (day 22, 02:00-06:00)
        if day == 22 and 2 <= hour <= 6:
            cpu = 85 + random.gauss(0, 5)
            mem = 82 + random.gauss(0, 4)
            error_rate = 0.30 + random.uniform(0, 0.25)

        # Inject a brief failure (day 22, 04:00-05:00)
        if day == 22 and 4 <= hour <= 5:
            error_rate = 0.55 + random.uniform(0, 0.15)

        # Inject a second degradation wave (day 15)
        if day == 15 and 8 <= hour <= 20:
            cpu += 25 + random.uniform(0, 8)
            mem += 15 + random.uniform(0, 5)

        # Clamp values to realistic ranges
        cpu = max(5, min(98, cpu))
        mem = max(20, min(95, mem))
        disk = max(20, min(95, disk))
        error_rate = max(0.001, min(0.95, error_rate))

        data.append({
            "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "cpu": round(cpu, 1),
            "mem": round(mem, 1),
            "disk": round(disk, 1),
            "error_rate": round(error_rate, 3),
        })

    return data


def write_raw_metrics(data, filepath):
    """Write raw continuous metrics to CSV."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "cpu", "mem", "disk", "error_rate"])
        writer.writeheader()
        writer.writerows(data)
    print(f"  ✅ {filepath} ({len(data)} rows)")


def write_state_log(data, filepath):
    """Write metrics with state column appended."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f,
                                fieldnames=["timestamp", "cpu", "mem", "disk", "error_rate", "state"])
        writer.writeheader()
        for row in data:
            row_with_state = dict(row)
            row_with_state["state"] = map_state(
                row["cpu"], row["mem"], row["disk"], row["error_rate"]
            )
            writer.writerow(row_with_state)
    print(f"  ✅ {filepath} ({len(data)} rows)")


def print_stats(filepath):
    """Print state distribution statistics."""
    from collections import Counter
    with open(filepath) as f:
        states = [row["state"] for row in csv.DictReader(f)]

    total = len(states)
    counts = Counter(states)

    print(f"\n{'═' * 60}")
    print(f"  State Distribution ({total} data points)")
    print(f"{'═' * 60}")

    for state in STATES:
        count = counts.get(state, 0)
        pct = (count / total) * 100
        bar_len = int(pct / 2.5)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        print(f"  {state:10s}: {count:4d} ({pct:5.1f}%)  {bar}")

    print(f"{'═' * 60}")

    # Print transition counts
    transitions = Counter(zip(states, states[1:]))
    print(f"\n  Top 10 Transitions:")
    for (s1, s2), count in transitions.most_common(10):
        print(f"    {s1:10s} → {s2:10s}: {count:4d}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Generate state data for Markov chain analysis")
    parser.add_argument("--days", type=int, default=30, help="Number of days to generate (default: 30)")
    parser.add_argument("--stats", action="store_true", help="Print state distribution statistics")
    args = parser.parse_args()

    print(f"Generating {args.days}-day infrastructure metrics...\n")

    data = generate_metrics(days=args.days)

    raw_path = os.path.join(OUTPUT_DIR, "raw_metrics.csv")
    state_path = os.path.join(OUTPUT_DIR, "state_log.csv")

    write_raw_metrics(data, raw_path)
    write_state_log(data, state_path)

    print(f"\nDone! Data files are in data/")

    if args.stats:
        print_stats(state_path)


if __name__ == "__main__":
    main()
