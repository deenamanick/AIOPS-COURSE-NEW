#!/usr/bin/env python3
"""build_prompt.py — Collect incident data from all lab endpoints and assemble an LLM prompt.

Usage:
    python3 scripts/build_prompt.py --output prompts/incident_context.txt
    python3 scripts/build_prompt.py --include-logs --include-alerts --include-anomaly --include-forecast --output prompts/capstone_context.txt
"""

import argparse
import json
import sys
import os
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

LAB_URL = "http://localhost:5002"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_DIR = os.path.join(SCRIPT_DIR, "../prompts")


def _fetch(path: str) -> dict:
    try:
        r = requests.get(f"{LAB_URL}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ⚠️  Could not fetch {path}: {e}", file=sys.stderr)
        return {}


def _format_logs(logs: list) -> str:
    if not logs:
        return "  (no logs available)\n"
    lines = []
    for entry in logs:
        ts = entry.get("timestamp", "")[:19].replace("T", " ")
        level = entry.get("level", "INFO")
        source = entry.get("source", "unknown")
        msg = entry.get("message", "")
        lines.append(f"{ts}Z {level:<5} [{source}] {msg}")
    return "\n".join(lines)


def _format_alerts(alerts: list) -> str:
    if not alerts:
        return "  (no active alerts)\n"
    lines = []
    for a in alerts:
        ts = a.get("timestamp", "")[:19].replace("T", " ")
        name = a.get("alertname", "unknown")
        sev = a.get("severity", "?")
        val = a.get("value", "?")
        unit = a.get("unit", "")
        lines.append(f"[FIRING] {name} | severity={sev} | value={val}{unit} | at {ts}Z")
    return "\n".join(lines)


def build_prompt(args) -> str:
    """Fetch incident data and assemble the LLM prompt."""
    print(f"Fetching incident data from {LAB_URL}...")

    # Always fetch metrics
    metrics = _fetch("/api/metrics")
    context_data = _fetch("/api/incident-context") if not args.no_context else {}

    sections = []
    sections.append("=== INCIDENT CONTEXT ===")
    sections.append(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    sections.append(f"Environment: training\n")

    # Metrics
    sections.append("=== CURRENT METRICS ===")
    if metrics:
        for k, v in metrics.items():
            if k != "timestamp":
                sections.append(f"  {k}: {v}")
    sections.append("")

    # Alerts
    alerts = context_data.get("active_alerts") or _fetch("/api/alerts") if args.include_alerts else []
    sections.append("=== ACTIVE ALERTS ===")
    sections.append(_format_alerts(alerts) if alerts else "  (no active alerts)")
    sections.append("")

    # Anomaly
    if args.include_anomaly:
        anomaly = context_data.get("anomaly") or _fetch("/api/anomaly")
        sections.append("=== ANOMALY SCORES (Module 5 engine) ===")
        if anomaly:
            sections.append(f"  Disk anomaly score:       {anomaly.get('disk_anomaly_score', '?')} / 100")
            sections.append(f"  Error rate anomaly score: {anomaly.get('error_rate_anomaly_score', '?')} / 100")
            sections.append(f"  Latency anomaly score:    {anomaly.get('latency_anomaly_score', '?')} / 100")
            sections.append(f"  Composite score:          {anomaly.get('composite_score', '?')} / 100  [{anomaly.get('severity', '?')}]")
        sections.append("")

    # Forecast
    if args.include_forecast:
        forecast = context_data.get("forecast") or _fetch("/api/forecast")
        sections.append("=== CAPACITY FORECAST (Module 9 engine) ===")
        if forecast and forecast.get("status") != "no-growth-active":
            sections.append(f"  Metric:         {forecast.get('metric', '?')}")
            sections.append(f"  Current:        {forecast.get('current_pct', '?')}%")
            sections.append(f"  Growth rate:    +{forecast.get('growth_rate_pct_per_hour', '?')}%/hr")
            sections.append(f"  Hours to 100%:  {forecast.get('hours_to_100_pct', '?')} hours")
            sections.append(f"  R² score:       {forecast.get('r2_score', '?')}")
            if forecast.get("alert_message"):
                sections.append(f"  ⚠️  {forecast['alert_message']}")
        else:
            sections.append("  Disk is stable — no growth trend detected.")
        sections.append("")

    # Logs
    if args.include_logs:
        logs = context_data.get("recent_logs") or _fetch("/api/logs?n=20")
        n = args.log_lines if hasattr(args, "log_lines") else 20
        sections.append(f"=== RECENT LOGS (last {n} lines) ===")
        sections.append(_format_logs(logs[:n] if isinstance(logs, list) else []))
        sections.append("")

    return "\n".join(sections)


def main():
    parser = argparse.ArgumentParser(description="Build an LLM incident prompt from lab data.")
    parser.add_argument("--output", default="prompts/incident_context.txt",
                        help="Output file path (default: prompts/incident_context.txt)")
    parser.add_argument("--include-logs", action="store_true", default=True,
                        help="Include recent log lines (default: true)")
    parser.add_argument("--include-alerts", action="store_true", default=True,
                        help="Include active alerts (default: true)")
    parser.add_argument("--include-anomaly", action="store_true", default=True,
                        help="Include anomaly scores (default: true)")
    parser.add_argument("--include-forecast", action="store_true", default=True,
                        help="Include disk forecast (default: true)")
    parser.add_argument("--log-lines", type=int, default=20,
                        help="Number of log lines to include (default: 20)")
    parser.add_argument("--no-context", action="store_true",
                        help="Do not use the /api/incident-context shortcut")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    prompt = build_prompt(args)

    with open(args.output, "w") as f:
        f.write(prompt)

    print(f"✅ Incident context written to: {args.output}")
    print(f"   Lines: {len(prompt.splitlines())}")
    print(f"   Characters: {len(prompt)}")
    print(f"\nPreview (first 10 lines):")
    for line in prompt.splitlines()[:10]:
        print(f"  {line}")


if __name__ == "__main__":
    main()
