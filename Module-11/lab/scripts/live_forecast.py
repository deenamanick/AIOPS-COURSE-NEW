#!/usr/bin/env python3
"""live_forecast.py — Fetch live disk metric from the lab and run a simple linear forecast.

Usage:
    python3 scripts/live_forecast.py --metric disk --output output/capstone_forecast.txt
"""

import argparse
import sys
import time
import os
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

try:
    import numpy as np
    from sklearn.linear_model import LinearRegression
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

LAB_URL = "http://localhost:5002"


def _collect_samples(metric_key: str, n_samples: int = 6, interval_sec: int = 10) -> list:
    """Collect n_samples data points at interval_sec apart."""
    samples = []
    print(f"  Collecting {n_samples} data points ({n_samples * interval_sec}s)...")
    for i in range(n_samples):
        try:
            m = requests.get(f"{LAB_URL}/api/metrics", timeout=5).json()
            val = m.get(f"{metric_key}_usage_pct") or m.get(metric_key)
            if val is not None:
                samples.append(float(val))
                print(f"    [{i+1}/{n_samples}] {metric_key}: {val}")
        except Exception as e:
            print(f"    ⚠️  Sample {i+1} failed: {e}")
        if i < n_samples - 1:
            time.sleep(interval_sec)
    return samples


def forecast_linear(samples: list, limit: float = 100.0) -> dict:
    """Fit a linear regression to the samples and forecast exhaustion."""
    if not HAS_SKLEARN or len(samples) < 3:
        # Fallback: simple mean growth rate
        if len(samples) >= 2:
            rate = (samples[-1] - samples[0]) / max(len(samples) - 1, 1)
        else:
            rate = 0
        hours_to_limit = (limit - samples[-1]) / rate if rate > 0 else None
        return {
            "current": round(samples[-1], 1),
            "growth_rate_per_interval": round(rate, 2),
            "hours_to_limit": round(hours_to_limit, 1) if hours_to_limit else None,
            "r2_score": None,
            "method": "mean-rate",
        }

    X = np.arange(len(samples)).reshape(-1, 1)
    y = np.array(samples)
    model = LinearRegression().fit(X, y)
    slope = float(model.coef_[0])
    r2 = round(float(model.score(X, y)), 2)

    if slope <= 0:
        return {
            "current": round(samples[-1], 1),
            "slope_per_sample": round(slope, 4),
            "r2_score": r2,
            "hours_to_limit": None,
            "message": "Metric is stable or declining. No exhaustion predicted.",
            "method": "linear-regression",
        }

    samples_to_limit = (limit - samples[-1]) / slope
    hours_to_limit = samples_to_limit * (10 / 3600)  # 10s per sample → hours

    return {
        "current": round(samples[-1], 1),
        "slope_per_sample": round(slope, 4),
        "growth_rate_pct_per_hour": round(slope * 360, 1),  # 360 samples/hr at 10s
        "r2_score": r2,
        "hours_to_limit": round(hours_to_limit, 2),
        "method": "linear-regression",
    }


def main():
    parser = argparse.ArgumentParser(description="Live metric forecast for the capstone.")
    parser.add_argument("--metric", default="disk",
                        choices=["disk", "cpu", "memory"],
                        help="Metric to forecast (default: disk)")
    parser.add_argument("--samples", type=int, default=6,
                        help="Number of data points to collect (default: 6)")
    parser.add_argument("--interval", type=int, default=10,
                        help="Seconds between samples (default: 10)")
    parser.add_argument("--output", default=None,
                        help="Save output to this file")
    args = parser.parse_args()

    print(f"\n{'═'*65}")
    print(f"  Live {args.metric.capitalize()} Forecast (Capstone)")
    print(f"{'═'*65}")

    # Try to use the built-in forecast from the drill (faster)
    forecast_from_api = None
    if args.metric == "disk":
        try:
            f = requests.get(f"{LAB_URL}/api/forecast", timeout=5).json()
            if f.get("status") != "no-growth-active":
                forecast_from_api = f
        except Exception:
            pass

    if forecast_from_api:
        result = {
            "current": forecast_from_api.get("current_pct"),
            "growth_rate_pct_per_hour": forecast_from_api.get("growth_rate_pct_per_hour"),
            "hours_to_limit": forecast_from_api.get("hours_to_100_pct"),
            "r2_score": forecast_from_api.get("r2_score"),
            "method": "api-forecast",
        }
        data_points = "N/A (from API)"
    else:
        samples = _collect_samples(args.metric, args.samples, args.interval)
        if not samples:
            print("❌ No samples collected. Is the lab running?")
            sys.exit(1)
        result = forecast_linear(samples)
        data_points = len(samples)

    current = result.get("current", "?")
    rate = result.get("growth_rate_pct_per_hour", "?")
    hours = result.get("hours_to_limit")
    r2 = result.get("r2_score", "N/A")

    lines = [
        f"{'═'*65}",
        f"  Live {args.metric.capitalize()} Forecast (Capstone)",
        f"{'═'*65}",
        f"  Data points:   {data_points}",
        f"  Current value: {current}%",
        f"  Growth rate:   +{rate}%/hr",
        f"  Hours to 100%: {hours if hours else 'stable — no exhaustion'}",
        f"  R² score:      {r2}",
    ]

    if hours and float(hours) < 3:
        predicted_time = (datetime.now(timezone.utc) + timedelta(hours=float(hours))).strftime("%Y-%m-%dT%H:%M:%SZ")
        lines.append(f"")
        lines.append(f"  🚨 PREDICTIVE ALERT: {args.metric.capitalize()} will exhaust in {hours:.1f} hours!")
        lines.append(f"  Predicted time: {predicted_time}")
        lines.append(f"  ⏰  Act now to prevent outage.")

    lines.append(f"{'═'*65}")

    output = "\n".join(lines)
    print(output)

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output)
        print(f"\n✅ Forecast saved to: {args.output}")


if __name__ == "__main__":
    main()
