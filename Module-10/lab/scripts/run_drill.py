#!/usr/bin/env python3
"""run_drill.py — Simulate a failure scenario and trigger the matching Ansible playbook.

Usage:
    python3 scripts/run_drill.py --scenario nginx-down
    python3 scripts/run_drill.py --scenario disk-full
    python3 scripts/run_drill.py --scenario high-load
"""

import argparse
import subprocess
import sys
import time
import requests

LAB_URL = "http://localhost:5001"

SCENARIOS = {
    "nginx-down": {
        "drill_endpoint": "/drill/nginx-down",
        "alert_name": "NginxDown",
        "playbook": "restart-service.yml",
        "verify_key": "nginx_up",
        "verify_value": True,
        "description": "Kill Nginx and verify restart-service.yml brings it back.",
    },
    "disk-full": {
        "drill_endpoint": "/drill/disk-spike",
        "alert_name": "DiskAlmostFull",
        "playbook": "clear-logs.yml",
        "verify_key": "disk_usage_pct",
        "verify_op": "lt",
        "verify_value": 80,
        "description": "Spike disk to 90% and verify clear-logs.yml cleans it up.",
    },
    "high-load": {
        "drill_endpoint": "/drill/cpu-spike",
        "alert_name": "HighCPULoad",
        "playbook": "scale-up.yml",
        "verify_key": "cpu_usage_pct",
        "verify_op": "lt",
        "verify_value": 75,
        "description": "Spike CPU to 85% and verify scale-up.yml adds a replica.",
    },
}


def _print_separator():
    print("═" * 65)


def _check_metric(metrics: dict, key: str, expected, op: str = "eq") -> bool:
    actual = metrics.get(key)
    if actual is None:
        return False
    if op == "eq":
        return actual == expected
    if op == "lt":
        return actual < expected
    return False


def main():
    parser = argparse.ArgumentParser(description="Run a Module 10 chaos drill.")
    parser.add_argument("--scenario", required=True, choices=SCENARIOS.keys(),
                        help="The failure scenario to simulate.")
    args = parser.parse_args()

    scenario = SCENARIOS[args.scenario]
    _print_separator()
    print(f"  Module 10 Drill: {args.scenario}")
    print(f"  {scenario['description']}")
    _print_separator()

    # Step 1: Check lab is running
    try:
        r = requests.get(f"{LAB_URL}/health", timeout=5)
        r.raise_for_status()
        print(f"✅ Lab is running at {LAB_URL}")
    except Exception as e:
        print(f"❌ Lab not reachable at {LAB_URL}: {e}")
        print("   Start it with: docker compose up -d --build")
        sys.exit(1)

    # Step 2: Inject the failure
    inject_time = time.time()
    print(f"\n[1/4] Injecting failure: {scenario['drill_endpoint']}")
    r = requests.post(f"{LAB_URL}{scenario['drill_endpoint']}")
    print(f"      Response: {r.json()}")

    # Step 3: Run the playbook manually
    playbook = scenario["playbook"]
    print(f"\n[2/4] Running Ansible playbook: {playbook}")
    result = subprocess.run(
        ["ansible-playbook", "-i", "playbooks/inventory.ini",
         f"playbooks/{playbook}", "--connection=local"],
        capture_output=False,  # Show output to terminal
        text=True,
    )
    playbook_duration = time.time() - inject_time

    if result.returncode != 0:
        print(f"\n❌ Playbook FAILED (exit code {result.returncode})")
        sys.exit(1)

    # Step 4: Verify recovery
    print(f"\n[3/4] Verifying recovery (polling for up to 60 seconds)...")
    deadline = time.time() + 60
    recovered = False
    while time.time() < deadline:
        try:
            metrics = requests.get(f"{LAB_URL}/api/metrics", timeout=5).json()
            key = scenario["verify_key"]
            op = scenario.get("verify_op", "eq")
            expected = scenario["verify_value"]
            if _check_metric(metrics, key, expected, op):
                recovered = True
                break
        except Exception:
            pass
        time.sleep(5)

    ttr = round(time.time() - inject_time, 1)
    _print_separator()
    if recovered:
        print(f"  ✅ PASS — {args.scenario}")
        print(f"  Playbook:    {playbook}")
        print(f"  TTR:         {ttr}s (time to full recovery from injection)")
    else:
        print(f"  ❌ FAIL — Metric did not recover within 60 seconds")
        print(f"  Check: curl -s {LAB_URL}/api/metrics | python3 -m json.tool")

    _print_separator()


if __name__ == "__main__":
    main()
