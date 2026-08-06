#!/usr/bin/env python3
"""
Generate 30 days of simulated infrastructure metrics for forecasting labs.

Outputs:
  data/disk_usage.csv    — steady growth (~0.7%/day)
  data/cpu_usage.csv     — noisy oscillation with slight upward trend
  data/memory_usage.csv  — step increases on simulated deploy days
"""

import csv
import os
import random
from datetime import datetime, timedelta

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def generate_disk_data(days=30, start_value=42.0, daily_growth=0.7):
    """Steady linear growth with minor daily noise."""
    data = []
    value = start_value
    base_date = datetime(2026, 7, 1)
    for day in range(days):
        date = base_date + timedelta(days=day)
        noise = random.uniform(-0.15, 0.15)
        value += daily_growth + noise
        data.append((date.strftime("%Y-%m-%d"), round(value, 1)))
    return data


def generate_cpu_data(days=30, base_value=35.0):
    """Noisy oscillation with slight upward trend (~0.2%/day)."""
    data = []
    value = base_value
    base_date = datetime(2026, 7, 1)
    for day in range(days):
        date = base_date + timedelta(days=day)
        # Daily pattern: higher during weekdays
        weekday_boost = 8 if date.weekday() < 5 else -5
        noise = random.uniform(-10, 10)
        trend = 0.2 * day
        value = base_value + trend + weekday_boost + noise
        value = max(5, min(95, value))
        data.append((date.strftime("%Y-%m-%d"), round(value, 1)))
    return data


def generate_memory_data(days=30, start_value=45.0):
    """Step increases on simulated deploy days (every ~5 days)."""
    data = []
    value = start_value
    base_date = datetime(2026, 7, 1)
    for day in range(days):
        date = base_date + timedelta(days=day)
        noise = random.uniform(-1.5, 1.5)
        # Step increase every ~5 days (simulating deployments that add memory load)
        if day > 0 and day % 5 == 0:
            value += random.uniform(2.0, 4.0)
        data.append((date.strftime("%Y-%m-%d"), round(value + noise, 1)))
    return data


def write_csv(filename, data):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "value"])
        writer.writerows(data)
    print(f"  ✅ {filename} ({len(data)} rows)")


def main():
    print("Generating 30-day training data...\n")

    write_csv(os.path.join(OUTPUT_DIR, "disk_usage.csv"), generate_disk_data())
    write_csv(os.path.join(OUTPUT_DIR, "cpu_usage.csv"), generate_cpu_data())
    write_csv(os.path.join(OUTPUT_DIR, "memory_usage.csv"), generate_memory_data())

    print("\nDone! Data files are in data/")


if __name__ == "__main__":
    main()
