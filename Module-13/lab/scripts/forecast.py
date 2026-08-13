#!/usr/bin/env python3
"""
Markov Chain Failure Forecaster — Module 13

Given a current state and a transition matrix, compute the probability
of reaching the 'Failed' state within N time steps. If the probability
exceeds a threshold, trigger a webhook to an Ansible remediation playbook.

Usage:
  python3 forecast.py --state Critical --matrix data/transition_matrix.csv
  python3 forecast.py --state Critical --matrix data/transition_matrix.csv --steps 13
  python3 forecast.py --state Critical --matrix data/transition_matrix.csv --threshold 0.50
  python3 forecast.py --state Degraded --matrix data/transition_matrix.csv --quiet
"""

import argparse
import csv
import os
import sys
import numpy as np

STATES = ["Healthy", "Degraded", "Critical", "Failed"]
STEP_MINUTES = 5  # Each step represents 5 minutes


def load_matrix(filepath: str) -> np.ndarray:
    """Load a transition matrix from CSV."""
    with open(filepath) as f:
        reader = csv.reader(f)
        header = next(reader)  # skip header row
        matrix = []
        for row in reader:
            matrix.append([float(v) for v in row[1:]])  # skip state label column
    return np.array(matrix)


def forecast_failure(matrix: np.ndarray, start_state: str,
                     steps: int) -> list[dict]:
    """Compute state distribution at each step via matrix multiplication."""
    vec = np.zeros(len(STATES))
    vec[STATES.index(start_state)] = 1.0
    failed_idx = STATES.index("Failed")

    results = []
    for step in range(1, steps + 1):
        vec = vec @ matrix
        results.append({
            "step": step,
            "distribution": {s: float(vec[i]) for i, s in enumerate(STATES)},
            "p_failed": float(vec[failed_idx]),
        })
    return results


def trigger_webhook(payload: dict, webhook_url: str):
    """Send a remediation webhook via HTTP POST."""
    try:
        import requests
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        print(f"  ✅ Webhook delivered successfully")
    except ImportError:
        print(f"  ⚠️  requests not installed. Webhook payload:")
        import json
        print(f"  {json.dumps(payload, indent=2)}")
    except Exception as exc:
        print(f"  ❌ Webhook delivery failed: {exc}")


def print_report(start_state: str, results: list[dict], threshold: float,
                 steps: int, quiet: bool = False):
    """Print the formatted forecast report."""
    final_p = results[-1]["p_failed"]
    horizon_min = steps * STEP_MINUTES
    exceeded = final_p >= threshold

    if quiet:
        status = "⚠️ WEBHOOK TRIGGERED" if exceeded else "✅"
        print(f"  {start_state:10s} → P(Failed) at step {steps}: "
              f"{final_p:5.1%}  {status}")
        return

    print(f"\n{'═' * 60}")
    print(f"  Markov Chain Failure Forecast")
    print(f"{'═' * 60}")
    print(f"  Current state:     {start_state}")
    print(f"  Time step:         {STEP_MINUTES} minutes")
    print(f"  Forecast horizon:  {steps} steps ({horizon_min} minutes)")
    print(f"  Threshold:         {threshold:.0%}")
    print()
    print(f"  Step-by-Step Forecast:")

    for r in results:
        marker = ""
        if r["p_failed"] >= threshold:
            marker = "  ⚠️"
        print(f"    Step {r['step']:2d}:  P(Failed) = {r['p_failed']:5.1%}{marker}")

    print()
    print(f"  Final P(Failed) at step {steps}: {final_p:.1%}")

    if exceeded:
        print(f"  ⚠️ THRESHOLD EXCEEDED — Triggering remediation webhook!")
    else:
        print(f"  ✅ Below threshold ({threshold:.0%}). No remediation needed.")

    print(f"{'═' * 60}")


def main():
    parser = argparse.ArgumentParser(description="Markov chain failure forecaster")
    parser.add_argument("--state", required=True, choices=STATES,
                        help="Current system state")
    parser.add_argument("--matrix", required=True,
                        help="Path to transition matrix CSV")
    parser.add_argument("--steps", type=int, default=6,
                        help="Number of time steps to forecast (default: 6)")
    parser.add_argument("--threshold", type=float, default=0.60,
                        help="P(Failed) threshold for webhook trigger (default: 0.60)")
    parser.add_argument("--webhook", default="http://localhost:5001/ansible-trigger",
                        help="Webhook URL for remediation (default: localhost:5001)")
    parser.add_argument("--quiet", action="store_true",
                        help="One-line output (useful for batch runs)")
    args = parser.parse_args()

    if not os.path.exists(args.matrix):
        sys.exit(f"❌ {args.matrix} not found. Run build_transition_matrix.py first.")

    matrix = load_matrix(args.matrix)

    # Validate matrix shape
    if matrix.shape != (4, 4):
        sys.exit(f"❌ Matrix shape is {matrix.shape}, expected (4, 4)")

    results = forecast_failure(matrix, args.state, args.steps)
    print_report(args.state, results, args.threshold, args.steps, args.quiet)

    # Trigger webhook if threshold exceeded
    final_p = results[-1]["p_failed"]
    if final_p >= args.threshold:
        from datetime import datetime, timezone
        payload = {
            "source": "markov-forecaster",
            "current_state": args.state,
            "p_failed": round(final_p, 4),
            "threshold": args.threshold,
            "steps": args.steps,
            "time_horizon_minutes": args.steps * STEP_MINUTES,
            "recommended_action": "scale-up",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if not args.quiet:
            print(f"\n  📡 POST {args.webhook}")
        trigger_webhook(payload, args.webhook)


if __name__ == "__main__":
    main()
