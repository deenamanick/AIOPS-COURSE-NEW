#!/usr/bin/env python3
"""traffic_gen.py — Generate HTTP traffic to the lab app and record every response.

Usage:
    python3 scripts/traffic_gen.py --duration 300 --rps 5
    python3 scripts/traffic_gen.py --duration 120 --rps 10 --output my_traffic.log
"""

import argparse
import time
import threading
import json
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    raise

LAB_URL = "http://localhost:5001"
_log_lock = threading.Lock()
_log_entries = []
_stop_event = threading.Event()


def _send_request(output_file: str):
    """Send one request and record the result."""
    ts = datetime.now(timezone.utc).isoformat()
    try:
        r = requests.get(f"{LAB_URL}/health", timeout=5)
        entry = {
            "timestamp": ts,
            "status_code": r.status_code,
            "latency_ms": round(r.elapsed.total_seconds() * 1000, 1),
            "ok": r.status_code == 200,
        }
    except requests.exceptions.ConnectionError:
        entry = {"timestamp": ts, "status_code": 0, "latency_ms": -1, "ok": False, "error": "connection-refused"}
    except requests.exceptions.Timeout:
        entry = {"timestamp": ts, "status_code": 0, "latency_ms": 5000, "ok": False, "error": "timeout"}

    with _log_lock:
        _log_entries.append(entry)
        if not entry["ok"]:
            print(f"  ⚠️  {entry['timestamp']} status={entry.get('status_code', '?')} latency={entry['latency_ms']}ms")


def main():
    parser = argparse.ArgumentParser(description="Generate traffic and record responses.")
    parser.add_argument("--duration", type=int, default=120, help="Duration in seconds (default: 120)")
    parser.add_argument("--rps", type=int, default=5, help="Requests per second (default: 5)")
    parser.add_argument("--output", default="traffic.log", help="Output log file (default: traffic.log)")
    args = parser.parse_args()

    print(f"Starting traffic generator: {args.rps} RPS for {args.duration}s → {args.output}")
    print("Errors will be printed as they occur. Press Ctrl+C to stop early.\n")

    interval = 1.0 / args.rps
    end_time = time.time() + args.duration

    try:
        while time.time() < end_time:
            t = threading.Thread(target=_send_request, args=(args.output,), daemon=True)
            t.start()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped by user.")

    # Write log
    with open(args.output, "w") as f:
        for entry in _log_entries:
            f.write(json.dumps(entry) + "\n")

    total = len(_log_entries)
    failed = sum(1 for e in _log_entries if not e["ok"])
    print(f"\nTraffic generation complete.")
    print(f"  Total requests:  {total}")
    print(f"  Successful:      {total - failed}")
    print(f"  Failed:          {failed}  ({round(failed / max(total, 1) * 100, 1)}%)")
    print(f"  Log saved to:    {args.output}")


if __name__ == "__main__":
    main()
