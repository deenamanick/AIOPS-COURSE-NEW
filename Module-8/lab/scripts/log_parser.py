#!/usr/bin/env python3
"""
Nginx Access Log Parser — Module 8

Reads plain-text Nginx combined log lines from stdin,
parses them into structured JSON, enriches with context,
and writes one JSON object per line to stdout.

Usage:
  cat access.log | python3 log_parser.py > parsed.json
"""

import json
import os
import re
import sys
import uuid
from datetime import datetime

PATTERN = re.compile(
    r'(?P<client_ip>\S+) \S+ \S+ '
    r'\[(?P<timestamp>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" '
    r'(?P<status>\d{3}) (?P<body_bytes>\d+) '
    r'"[^"]*" "(?P<user_agent>[^"]*)"'
    r'(?: (?P<request_time>[\d.]+))?'
)


def parse_line(line: str) -> dict | None:
    """Parse a single Nginx combined log line into a structured dict."""
    m = PATTERN.match(line.strip())
    if not m:
        return None
    d = m.groupdict()
    d["status"] = int(d["status"])
    d["body_bytes"] = int(d["body_bytes"])
    d["request_time_ms"] = int(float(d.pop("request_time") or "0") * 1000)
    try:
        d["timestamp"] = datetime.strptime(
            d["timestamp"], "%d/%b/%Y:%H:%M:%S %z"
        ).isoformat()
    except ValueError:
        pass  # Keep raw timestamp if parsing fails
    return d


def enrich(entry: dict) -> dict:
    """Add contextual metadata not present in the raw log."""
    entry["hostname"] = os.environ.get("HOSTNAME", "unknown")
    entry["service"] = "nginx"
    entry["environment"] = os.environ.get("ENVIRONMENT", "training")
    entry["trace_id"] = str(uuid.uuid4())
    return entry


def main():
    parsed = 0
    failed = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        entry = parse_line(line)
        if entry:
            entry = enrich(entry)
            print(json.dumps(entry))
            parsed += 1
        else:
            print(f"WARN: Could not parse: {line[:80]}...", file=sys.stderr)
            failed += 1

    print(f"\nParsed: {parsed} lines, Failed: {failed} lines", file=sys.stderr)


if __name__ == "__main__":
    main()
