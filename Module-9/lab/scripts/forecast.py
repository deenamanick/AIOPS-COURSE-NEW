#!/usr/bin/env python3
"""
Time-Series Forecasting Engine — Module 9

Loads CSV data (date, value), fits a linear regression model,
predicts when the metric will reach the capacity limit,
and generates a forecast plot.

Usage:
  python3 forecast.py                              # Process all default CSVs
  python3 forecast.py --input data/disk_usage.csv  # Process a specific file
  python3 forecast.py --input data/live.csv --limit 100
"""

import argparse
import csv
import os
import sys
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


def load_csv(filepath: str) -> tuple[list[datetime], list[float]]:
    dates, values = [], []
    with open(filepath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            dates.append(datetime.strptime(row["date"].split("T")[0], "%Y-%m-%d"))
            values.append(float(row["value"]))
    return dates, values


def forecast_exhaustion(dates, values, limit=100.0):
    base = dates[0]
    X = np.array([(d - base).days for d in dates]).reshape(-1, 1)
    y = np.array(values)

    model = LinearRegression()
    model.fit(X, y)

    slope = model.coef_[0]
    intercept = model.intercept_
    r_squared = model.score(X, y)

    if slope <= 0:
        return {
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared,
            "current": values[-1],
            "days_to_limit": None,
            "exhaustion_date": None,
            "model": model,
            "X": X,
            "y": y,
            "base": base,
        }

    days_to_limit = (limit - values[-1]) / slope
    exhaustion_date = dates[-1] + timedelta(days=int(days_to_limit))

    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": r_squared,
        "current": values[-1],
        "days_to_limit": int(days_to_limit),
        "exhaustion_date": exhaustion_date,
        "model": model,
        "X": X,
        "y": y,
        "base": base,
    }


def moving_average(values, window=7):
    return [np.mean(values[max(0, i - window + 1):i + 1]) for i in range(len(values))]


def generate_plot(name, dates, result, limit=100.0):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        print("  ⚠️  matplotlib not installed. Skipping plot generation.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6))

    # Actual values
    ax.scatter(dates, result["y"], color="#4338ca", s=30, zorder=5, label="Actual")

    # Moving average
    ma = moving_average(list(result["y"]), 7)
    ax.plot(dates, ma, color="#6366f1", linewidth=1.5, alpha=0.5, label="7-day Moving Avg")

    # Regression line (extended to exhaustion)
    if result["exhaustion_date"]:
        extend_days = result["days_to_limit"] + 5
        X_ext = np.arange(0, len(dates) + extend_days).reshape(-1, 1)
        y_ext = result["model"].predict(X_ext)
        dates_ext = [result["base"] + timedelta(days=int(d)) for d in X_ext.flatten()]
        ax.plot(dates_ext, y_ext, color="#dc2626", linewidth=2, linestyle="--",
                label=f"Forecast (R²={result['r_squared']:.2f})")

        # Exhaustion line
        ax.axvline(x=result["exhaustion_date"], color="#dc2626", linewidth=1.5,
                   linestyle=":", alpha=0.8)
        ax.annotate(f"Predicted: {result['exhaustion_date'].strftime('%Y-%m-%d')}",
                    xy=(result["exhaustion_date"], limit),
                    xytext=(result["exhaustion_date"] - timedelta(days=10), limit - 10),
                    fontsize=9, color="#dc2626", fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color="#dc2626"))

    # Color zones
    ax.axhspan(0, 80, alpha=0.05, color="green", label="Safe (< 80%)")
    ax.axhspan(80, 90, alpha=0.08, color="orange", label="Warning (80–90%)")
    ax.axhspan(90, 110, alpha=0.08, color="red", label="Critical (> 90%)")

    ax.set_title(f"{name} — Capacity Forecast", fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Usage (%)")
    ax.set_ylim(0, 110)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    plt.tight_layout()

    filename = os.path.join(OUTPUT_DIR, f"{name.lower().replace(' ', '_')}_forecast.png")
    plt.savefig(filename, dpi=150)
    plt.close()
    print(f"  📊 Plot saved: {filename}")


def print_report(name, result, limit=100.0):
    print(f"\n{'═' * 60}")
    print(f"  {name} Forecast")
    print(f"{'═' * 60}")
    print(f"  Current value:     {result['current']:.1f}%")
    print(f"  Daily growth rate: {'+' if result['slope'] > 0 else ''}{result['slope']:.2f}%/day")
    print(f"  R² score:          {result['r_squared']:.2f} "
          f"({'strong' if result['r_squared'] > 0.9 else 'moderate' if result['r_squared'] > 0.7 else 'weak'} linear fit)")

    if result["days_to_limit"]:
        print(f"  Days to {limit:.0f}%:      {result['days_to_limit']} days")
        print(f"  Predicted date:    {result['exhaustion_date'].strftime('%Y-%m-%d')}")

        if result["days_to_limit"] < 30:
            print(f"\n  🚨 ALERT: Metric will exhaust in < 30 days. Immediate action needed.")
        elif result["days_to_limit"] < 60:
            print(f"\n  ⚠️  WARNING: Metric will exhaust in < 60 days. Plan capacity expansion.")
        else:
            print(f"\n  ✅ OK: Metric has > 60 days of headroom.")
    else:
        print(f"\n  ✅ Metric is stable or declining. No exhaustion predicted.")

    print(f"{'═' * 60}")


def main():
    parser = argparse.ArgumentParser(description="Time-series forecasting engine")
    parser.add_argument("--input", help="Path to a specific CSV file")
    parser.add_argument("--limit", type=float, default=100.0, help="Capacity limit (default: 100)")
    args = parser.parse_args()

    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")

    if args.input:
        files = [(os.path.splitext(os.path.basename(args.input))[0].replace("_", " ").title(),
                  args.input)]
    else:
        files = [
            ("Disk Usage", os.path.join(data_dir, "disk_usage.csv")),
            ("CPU Usage", os.path.join(data_dir, "cpu_usage.csv")),
            ("Memory Usage", os.path.join(data_dir, "memory_usage.csv")),
        ]

    for name, filepath in files:
        if not os.path.exists(filepath):
            print(f"  ⚠️  {filepath} not found. Run generate_data.py first.")
            continue

        dates, values = load_csv(filepath)
        result = forecast_exhaustion(dates, values, limit=args.limit)
        print_report(name, result, limit=args.limit)
        generate_plot(name, dates, result, limit=args.limit)


if __name__ == "__main__":
    main()
