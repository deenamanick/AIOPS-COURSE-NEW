#!/usr/bin/env python3
"""
Predictive Alert Scheduler — Module 9

Sets a predictive alert on the lab's Flask app that will fire
before the forecasted exhaustion time.

Usage:
  python3 set_predictive_alert.py --metric disk \
      --predicted-exhaustion "2026-08-06T21:54:00Z" \
      --lead-time-hours 2
"""

import argparse
import json
import urllib.request


def main():
    parser = argparse.ArgumentParser(description="Set a predictive alert")
    parser.add_argument("--metric", default="disk", help="Metric name")
    parser.add_argument("--predicted-exhaustion", required=True,
                        help="Predicted exhaustion time (ISO 8601)")
    parser.add_argument("--lead-time-hours", type=int, default=2,
                        help="Hours before predicted failure to fire alert")
    parser.add_argument("--url", default="http://localhost:5000/drill/set-alert",
                        help="Alert endpoint URL")
    args = parser.parse_args()

    payload = json.dumps({
        "predicted_exhaustion": args.predicted_exhaustion,
        "lead_hours": args.lead_time_hours,
    }).encode()

    req = urllib.request.Request(
        args.url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            print(f"\n[ALERT SCHEDULER] Predictive alert set:")
            print(f"  Metric:            {args.metric}")
            print(f"  Predicted failure:  {args.predicted_exhaustion}")
            print(f"  Alert fires at:     {args.lead_time_hours}h before predicted failure")
            print(f"  Status:            ARMED ✅\n")
    except Exception as e:
        print(f"❌ Failed to set alert: {e}")
        print("Make sure the lab is running: docker compose up -d")


if __name__ == "__main__":
    main()
