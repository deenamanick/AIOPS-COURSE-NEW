#!/usr/bin/env python3
"""
DORA Metrics Calculator — Module 9

Calculates Deployment Frequency, Lead Time for Changes,
Change Failure Rate, and Mean Time to Restore from workflow run data.

Usage:
  python3 dora_calculator.py
  python3 dora_calculator.py --input data/workflow_runs.csv
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta
from collections import Counter

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def generate_sample_data(filepath):
    """Generate sample workflow run data if not present."""
    import random
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    runs = []
    base = datetime(2026, 7, 1)
    run_id = 10000

    for day in range(30):
        date = base + timedelta(days=day)
        # Skip some weekends
        if date.weekday() >= 5 and random.random() < 0.6:
            continue

        # 1–3 deployments per active day
        num_deploys = random.randint(1, 3)
        for i in range(num_deploys):
            run_id += 1
            hour = random.randint(9, 17)
            created = date.replace(hour=hour, minute=random.randint(0, 59))
            duration_min = random.randint(3, 12)
            completed = created + timedelta(minutes=duration_min)

            # ~12% failure rate
            conclusion = "failure" if random.random() < 0.12 else "success"

            runs.append({
                "run_id": run_id,
                "workflow": "deploy.yml",
                "conclusion": conclusion,
                "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "completed_at": completed.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "event": "push",
                "head_sha": f"{random.randint(100000, 999999):x}",
            })

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "run_id", "workflow", "conclusion", "created_at", "completed_at", "event", "head_sha"
        ])
        writer.writeheader()
        writer.writerows(runs)

    print(f"  ✅ Generated {len(runs)} sample workflow runs → {filepath}")
    return runs


def load_runs(filepath):
    runs = []
    with open(filepath) as f:
        for row in csv.DictReader(f):
            runs.append(row)
    return runs


def deployment_frequency(deploys, days):
    successful = [d for d in deploys if d["conclusion"] == "success"]
    per_day = len(successful) / max(days, 1)
    per_week = per_day * 7

    if per_day >= 1:
        tier = "Elite"
        emoji = "🏆"
    elif per_week >= 1:
        tier = "High"
        emoji = "🟢"
    elif per_week >= 0.25:
        tier = "Medium"
        emoji = "🟡"
    else:
        tier = "Low"
        emoji = "🔴"

    return {
        "successful": len(successful),
        "total": len(deploys),
        "per_day": round(per_day, 2),
        "per_week": round(per_week, 2),
        "tier": tier,
        "emoji": emoji,
    }


def lead_time(deploys):
    durations = []
    for d in deploys:
        if d["conclusion"] == "success":
            created = datetime.strptime(d["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            completed = datetime.strptime(d["completed_at"], "%Y-%m-%dT%H:%M:%SZ")
            durations.append((completed - created).total_seconds() / 3600)

    if not durations:
        return {"median_hours": None, "tier": "Unknown", "emoji": "❓"}

    durations.sort()
    median = durations[len(durations) // 2]

    if median < 1:
        tier, emoji = "Elite", "🏆"
    elif median < 24:
        tier, emoji = "High", "🟢"
    elif median < 168:
        tier, emoji = "Medium", "🟡"
    else:
        tier, emoji = "Low", "🔴"

    return {"median_hours": round(median, 2), "median_minutes": round(median * 60, 1),
            "tier": tier, "emoji": emoji}


def change_failure_rate(deploys):
    total = len(deploys)
    failures = sum(1 for d in deploys if d["conclusion"] == "failure")

    if total == 0:
        return {"rate": 0, "tier": "Unknown", "emoji": "❓"}

    rate = (failures / total) * 100

    if rate <= 15:
        tier, emoji = "Elite", "🏆"
    elif rate <= 30:
        tier, emoji = "High/Medium", "🟡"
    else:
        tier, emoji = "Low", "🔴"

    return {"rate": round(rate, 1), "failures": failures, "total": total,
            "tier": tier, "emoji": emoji}


def mean_time_to_restore(deploys):
    restore_times = []
    last_failure_time = None

    for d in sorted(deploys, key=lambda x: x["created_at"]):
        if d["conclusion"] == "failure":
            last_failure_time = datetime.strptime(d["completed_at"], "%Y-%m-%dT%H:%M:%SZ")
        elif d["conclusion"] == "success" and last_failure_time:
            restored = datetime.strptime(d["completed_at"], "%Y-%m-%dT%H:%M:%SZ")
            restore_times.append((restored - last_failure_time).total_seconds() / 3600)
            last_failure_time = None

    if not restore_times:
        return {"median_hours": None, "tier": "Unknown", "emoji": "❓"}

    restore_times.sort()
    median = restore_times[len(restore_times) // 2]

    if median < 1:
        tier, emoji = "Elite", "🏆"
    elif median < 24:
        tier, emoji = "High", "🟢"
    elif median < 168:
        tier, emoji = "Medium", "🟡"
    else:
        tier, emoji = "Low", "🔴"

    return {"median_hours": round(median, 2), "tier": tier, "emoji": emoji}


def generate_dashboard(freq, lt, cfr, mttr_result):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("\n  ⚠️  matplotlib not installed. Skipping dashboard generation.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle("DORA Metrics Dashboard", fontsize=16, fontweight="bold")

    tier_colors = {"Elite": "#4338ca", "High": "#22c55e", "High/Medium": "#eab308",
                   "Medium": "#eab308", "Low": "#ef4444", "Unknown": "#94a3b8"}

    # 1. Deployment Frequency
    ax = axes[0, 0]
    ax.bar(["Your Team"], [freq["per_day"]], color=tier_colors[freq["tier"]], width=0.4)
    ax.axhline(y=1, color="#4338ca", linewidth=1, linestyle="--", alpha=0.5, label="Elite: 1+/day")
    ax.set_title(f"Deploy Frequency ({freq['emoji']} {freq['tier']})")
    ax.set_ylabel("Deploys / Day")
    ax.legend(fontsize=7)

    # 2. Lead Time
    ax = axes[0, 1]
    val = lt["median_minutes"] if lt["median_minutes"] else 0
    ax.bar(["Your Team"], [val], color=tier_colors[lt["tier"]], width=0.4)
    ax.axhline(y=60, color="#4338ca", linewidth=1, linestyle="--", alpha=0.5, label="Elite: < 60 min")
    ax.set_title(f"Lead Time ({lt['emoji']} {lt['tier']})")
    ax.set_ylabel("Minutes (median)")
    ax.legend(fontsize=7)

    # 3. Change Failure Rate
    ax = axes[1, 0]
    ax.bar(["Your Team"], [cfr["rate"]], color=tier_colors[cfr["tier"]], width=0.4)
    ax.axhline(y=15, color="#4338ca", linewidth=1, linestyle="--", alpha=0.5, label="Elite: < 15%")
    ax.set_title(f"Change Failure Rate ({cfr['emoji']} {cfr['tier']})")
    ax.set_ylabel("Failure Rate (%)")
    ax.legend(fontsize=7)

    # 4. MTTR
    ax = axes[1, 1]
    val = mttr_result["median_hours"] if mttr_result["median_hours"] else 0
    ax.bar(["Your Team"], [val], color=tier_colors[mttr_result["tier"]], width=0.4)
    ax.axhline(y=1, color="#4338ca", linewidth=1, linestyle="--", alpha=0.5, label="Elite: < 1 hr")
    ax.set_title(f"MTTR ({mttr_result['emoji']} {mttr_result['tier']})")
    ax.set_ylabel("Hours (median)")
    ax.legend(fontsize=7)

    plt.tight_layout()
    filename = os.path.join(OUTPUT_DIR, "dora_dashboard.png")
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"\n  📊 Dashboard saved: {filename}")


def main():
    parser = argparse.ArgumentParser(description="DORA Metrics Calculator")
    parser.add_argument("--input", help="Path to workflow_runs.csv")
    args = parser.parse_args()

    filepath = args.input or os.path.join(DATA_DIR, "workflow_runs.csv")

    if not os.path.exists(filepath):
        print("  No workflow data found. Generating sample data...\n")
        generate_sample_data(filepath)

    runs = load_runs(filepath)
    days = 30

    freq = deployment_frequency(runs, days)
    lt = lead_time(runs)
    cfr = change_failure_rate(runs)
    mttr_result = mean_time_to_restore(runs)

    print(f"\n{'═' * 60}")
    print(f"  DORA Metrics Report")
    print(f"  Period: 30 days | Workflow runs analyzed: {len(runs)}")
    print(f"{'═' * 60}")

    print(f"\n  Deployment Frequency:   {freq['per_day']} / day ({freq['per_week']} / week)")
    print(f"  Tier: {freq['emoji']} {freq['tier']}")

    if lt["median_hours"]:
        print(f"\n  Lead Time for Changes:  {lt['median_hours']} hours ({lt['median_minutes']} min median)")
    else:
        print(f"\n  Lead Time for Changes:  N/A")
    print(f"  Tier: {lt['emoji']} {lt['tier']}")

    print(f"\n  Change Failure Rate:    {cfr['rate']}% ({cfr.get('failures', 0)} failures / "
          f"{cfr.get('total', 0)} deploys)")
    print(f"  Tier: {cfr['emoji']} {cfr['tier']}")

    if mttr_result["median_hours"]:
        print(f"\n  Mean Time to Restore:   {mttr_result['median_hours']} hours")
    else:
        print(f"\n  Mean Time to Restore:   N/A")
    print(f"  Tier: {mttr_result['emoji']} {mttr_result['tier']}")

    print(f"\n  {'─' * 56}")
    tiers = [freq["tier"], lt["tier"], cfr["tier"], mttr_result["tier"]]
    tier_set = set(t for t in tiers if t != "Unknown")
    overall = " / ".join(sorted(tier_set))
    print(f"  Overall DORA Tier:      {overall}")
    print(f"  {'─' * 56}")

    generate_dashboard(freq, lt, cfr, mttr_result)
    print()


if __name__ == "__main__":
    main()
