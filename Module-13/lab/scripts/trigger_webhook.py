#!/usr/bin/env python3
"""
Webhook client for triggering Ansible auto-remediation playbooks.

Sends a JSON payload to the configured webhook endpoint when the
Markov forecaster detects a high probability of failure.

Usage:
  python3 trigger_webhook.py --state Critical --probability 0.65
  python3 trigger_webhook.py --state Critical --probability 0.65 --url http://host:5001/ansible-trigger
  python3 trigger_webhook.py --dry-run --state Failed --probability 0.80
"""

import argparse
import json
import sys
from datetime import datetime, timezone

DEFAULT_WEBHOOK_URL = "http://localhost:5001/ansible-trigger"


def build_payload(state: str, probability: float, steps: int = 6,
                  action: str = "scale-up") -> dict:
    """Build the webhook JSON payload."""
    return {
        "source": "markov-forecaster",
        "current_state": state,
        "p_failed": round(probability, 4),
        "threshold": 0.60,
        "steps": steps,
        "time_horizon_minutes": steps * 5,
        "recommended_action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def send_webhook(url: str, payload: dict) -> bool:
    """Send the payload via HTTP POST. Returns True on success."""
    try:
        import requests
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        print(f"✅ Webhook delivered to {url}")
        print(f"   Response: {response.status_code} {response.text[:200]}")
        return True
    except ImportError:
        print("❌ requests not installed. Run: pip install requests")
        return False
    except Exception as exc:
        print(f"❌ Webhook failed: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Trigger Ansible remediation webhook")
    parser.add_argument("--state", required=True,
                        choices=["Healthy", "Degraded", "Critical", "Failed"],
                        help="Current system state")
    parser.add_argument("--probability", type=float, required=True,
                        help="Predicted failure probability (0.0–1.0)")
    parser.add_argument("--steps", type=int, default=6,
                        help="Forecast steps used (default: 6)")
    parser.add_argument("--action", default="scale-up",
                        choices=["restart-service", "clear-logs", "scale-up"],
                        help="Recommended remediation action")
    parser.add_argument("--url", default=DEFAULT_WEBHOOK_URL,
                        help=f"Webhook endpoint URL (default: {DEFAULT_WEBHOOK_URL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the payload without sending")
    args = parser.parse_args()

    payload = build_payload(args.state, args.probability, args.steps, args.action)

    if args.dry_run:
        print("🔍 Dry run — payload that would be sent:")
        print(json.dumps(payload, indent=2))
        return

    print(f"📡 Sending webhook to {args.url}")
    print(f"   State: {args.state} | P(Failed): {args.probability:.1%}")
    success = send_webhook(args.url, payload)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
