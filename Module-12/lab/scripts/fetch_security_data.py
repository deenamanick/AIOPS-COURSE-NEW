#!/usr/bin/env python3
"""
Module 12 — Fetch user behavior data from the lab app.
Writes JSON suitable for the security anomaly detector.
"""

import json
import argparse
import requests
from pathlib import Path

LAB_URL = "http://localhost:5003"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",  default="data/user_behavior.json")
    parser.add_argument("--lab-url", default=LAB_URL)
    args = parser.parse_args()

    print(f"Fetching user behavior data from {args.lab_url} ...")
    resp = requests.get(f"{args.lab_url}/api/user-behavior", timeout=10)
    resp.raise_for_status()
    sessions = resp.json()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(sessions, f, indent=2)

    print(f"Wrote {len(sessions)} sessions → {args.output}")


if __name__ == "__main__":
    main()
