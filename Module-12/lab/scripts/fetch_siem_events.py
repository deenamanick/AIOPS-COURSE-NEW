#!/usr/bin/env python3
"""
Module 12 — Fetch SIEM events from the lab app.
Writes JSON suitable for the SIEM correlation engine.
"""

import json
import argparse
import requests
from pathlib import Path

LAB_URL = "http://localhost:5003"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",  default="data/siem_events.json")
    parser.add_argument("--lab-url", default=LAB_URL)
    args = parser.parse_args()

    print(f"Fetching SIEM events from {args.lab_url} ...")
    resp = requests.get(f"{args.lab_url}/api/siem-events", timeout=10)
    resp.raise_for_status()
    events = resp.json()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(events, f, indent=2)

    sources = {}
    for e in events:
        sources[e.get("source", "?")] = sources.get(e.get("source", "?"), 0) + 1
    print(f"Wrote {len(events)} events → {args.output}")
    for src, count in sorted(sources.items()):
        print(f"  {src:12s}: {count} events")


if __name__ == "__main__":
    main()
