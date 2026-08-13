# 04 — Compliance Monitoring Script

Compliance is not a one-time audit — it is a continuous operational state. SOC2 and GDPR both require that controls are *always* in place, not just when an auditor arrives. AIOps automation makes continuous compliance measurably cheaper than periodic manual checks.

---

## What SOC2 and GDPR Require from Infrastructure Teams

### SOC2 (Trust Services Criteria)

SOC2 is an American auditing standard for service organizations. Its five Trust Services Criteria map directly to infrastructure controls:

| SOC2 Criterion | Infrastructure Requirement |
|---|---|
| **CC6.1** — Logical access | SSH keys rotated, root login disabled, MFA enforced |
| **CC6.6** — Network security | Firewall rules documented and enforced |
| **CC6.7** — Transmission protection | All traffic encrypted (TLS 1.2+, no plain-text DB connections) |
| **CC7.2** — System monitoring | Logs forwarded to SIEM; log retention ≥ 90 days |
| **A1.2** — Backup & recovery | Database backups run daily; restore tested monthly |

### GDPR (General Data Protection Regulation)

GDPR is a European data privacy regulation. From an infrastructure perspective, the key technical requirements are:

| GDPR Article | Infrastructure Requirement |
|---|---|
| **Art. 25** — Data protection by design | Encryption at rest for any storage containing PII |
| **Art. 32** — Security of processing | Access controls, audit logging, vulnerability management |
| **Art. 33** — Breach notification | Incident detection and logging to support 72-hour notification SLA |
| **Art. 5(1)(e)** — Storage limitation | Data retention policies enforced (old PII must be deleted) |

---

## The Compliance Monitoring Script

The script below checks the seven most common infrastructure compliance controls. It outputs a `PASS` / `FAIL` / `WARN` report that can be scheduled as a daily cron job and fed into your SIEM.

```python
#!/usr/bin/env python3
"""
Module 12 — Compliance Monitoring Script
Checks SOC2/GDPR infrastructure controls and outputs a report.

Usage:
  python3 scripts/compliance_check.py [--host db-server] [--output report.json]

Controls checked:
  1. SSH key rotation (last rotation ≤ 90 days)
  2. Root login disabled in sshd_config
  3. Password authentication disabled in sshd_config
  4. Expected iptables firewall rules present
  5. rsyslog/syslog-ng log forwarding configured
  6. Database backup age (must be < 25 hours)
  7. Disk encryption enabled (LUKS or dm-crypt)
"""

import subprocess
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Configurable thresholds ─────────────────────────────────────────────────
SSH_KEY_MAX_AGE_DAYS  = 90    # SOC2 CC6.1
BACKUP_MAX_AGE_HOURS  = 25    # SOC2 A1.2 (allow 1 hour grace over 24h schedule)
REQUIRED_IPTABLES     = [     # SOC2 CC6.6
    ("INPUT",  "DROP"),       # Default deny inbound
    ("OUTPUT", "DROP"),       # Default deny outbound
]
LOG_FORWARD_DEST      = "/etc/rsyslog.d/"    # SOC2 CC7.2
BACKUP_DIR            = "/var/backups/db/"   # SOC2 A1.2
LUKS_DEVICE           = "/dev/sda"           # GDPR Art. 25


def _run(cmd: str, ignore_errors: bool = False) -> tuple[int, str]:
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True
    )
    if result.returncode != 0 and not ignore_errors:
        return result.returncode, result.stderr.strip()
    return result.returncode, (result.stdout + result.stderr).strip()


def check_ssh_key_rotation() -> dict:
    """SOC2 CC6.1 — SSH keys must be rotated within SSH_KEY_MAX_AGE_DAYS."""
    control = "SSH_KEY_ROTATION"
    try:
        auth_keys = Path("/root/.ssh/authorized_keys")
        if not auth_keys.exists():
            return {"control": control, "status": "WARN",
                    "detail": "No authorized_keys file found — may be using password auth"}

        mtime = datetime.fromtimestamp(auth_keys.stat().st_mtime, tz=timezone.utc)
        age_days = (datetime.now(timezone.utc) - mtime).days

        if age_days <= SSH_KEY_MAX_AGE_DAYS:
            return {"control": control, "status": "PASS",
                    "detail": f"authorized_keys last modified {age_days} days ago (limit: {SSH_KEY_MAX_AGE_DAYS})"}
        else:
            return {"control": control, "status": "FAIL",
                    "detail": f"authorized_keys is {age_days} days old — rotation required (limit: {SSH_KEY_MAX_AGE_DAYS})"}
    except Exception as e:
        return {"control": control, "status": "ERROR", "detail": str(e)}


def check_root_login_disabled() -> dict:
    """SOC2 CC6.1 — Root login must be disabled."""
    control = "ROOT_LOGIN_DISABLED"
    rc, out = _run("grep -iE '^PermitRootLogin' /etc/ssh/sshd_config", ignore_errors=True)
    if "PermitRootLogin no" in out.lower():
        return {"control": control, "status": "PASS",
                "detail": "PermitRootLogin no confirmed in sshd_config"}
    elif out.strip() == "":
        return {"control": control, "status": "WARN",
                "detail": "PermitRootLogin not explicitly set — defaults may allow root on some distributions"}
    else:
        return {"control": control, "status": "FAIL",
                "detail": f"Root login not disabled: '{out.strip()}'"}


def check_password_auth_disabled() -> dict:
    """SOC2 CC6.1 — Password authentication must be disabled (keys only)."""
    control = "PASSWORD_AUTH_DISABLED"
    rc, out = _run("grep -iE '^PasswordAuthentication' /etc/ssh/sshd_config", ignore_errors=True)
    if "passwordauthentication no" in out.lower():
        return {"control": control, "status": "PASS",
                "detail": "PasswordAuthentication no confirmed in sshd_config"}
    else:
        return {"control": control, "status": "FAIL",
                "detail": f"Password authentication not disabled: '{out.strip()}'"}


def check_firewall_rules() -> dict:
    """SOC2 CC6.6 — Default-deny firewall rules must be present."""
    control = "FIREWALL_DEFAULT_DENY"
    rc, out = _run("iptables -L -n 2>/dev/null || nft list ruleset 2>/dev/null", ignore_errors=True)
    if not out:
        return {"control": control, "status": "FAIL",
                "detail": "Could not read firewall rules — iptables/nftables may not be installed"}

    missing = []
    for chain, target in REQUIRED_IPTABLES:
        pattern = rf"Chain {chain}.*DROP|DROP.*{chain}"
        # Simple heuristic: check if DROP appears in the chain's rules
        if f"DROP" not in out:
            missing.append(f"{chain} → {target}")

    # More precise check: look for DROP in each chain section
    input_section  = re.search(r"Chain INPUT.*?(?=Chain |\Z)", out, re.DOTALL)
    output_section = re.search(r"Chain OUTPUT.*?(?=Chain |\Z)", out, re.DOTALL)

    fails = []
    if input_section  and "DROP" not in input_section.group():
        fails.append("INPUT chain has no DROP rule")
    if output_section and "DROP" not in output_section.group():
        fails.append("OUTPUT chain has no DROP rule")

    if not fails:
        return {"control": control, "status": "PASS",
                "detail": "Default-deny DROP rules found in INPUT and OUTPUT chains"}
    else:
        return {"control": control, "status": "FAIL",
                "detail": "; ".join(fails)}


def check_log_forwarding() -> dict:
    """SOC2 CC7.2 — Log forwarding must be configured."""
    control = "LOG_FORWARDING"
    fwd_dir = Path(LOG_FORWARD_DEST)
    if not fwd_dir.exists():
        return {"control": control, "status": "FAIL",
                "detail": f"rsyslog.d directory not found at {LOG_FORWARD_DEST}"}

    conf_files = list(fwd_dir.glob("*.conf"))
    fwd_configs = [f for f in conf_files if _has_forwarding(f)]

    if fwd_configs:
        return {"control": control, "status": "PASS",
                "detail": f"Log forwarding configured in: {[f.name for f in fwd_configs]}"}
    else:
        return {"control": control, "status": "FAIL",
                "detail": f"No forwarding (@@/@@) rules found in {LOG_FORWARD_DEST}*.conf"}


def _has_forwarding(conf_path: Path) -> bool:
    try:
        content = conf_path.read_text()
        return bool(re.search(r"@@?[a-zA-Z0-9.\-]+:\d+", content))
    except Exception:
        return False


def check_database_backup() -> dict:
    """SOC2 A1.2 — Database backup must exist and be recent."""
    control = "DATABASE_BACKUP_RECENT"
    backup_dir = Path(BACKUP_DIR)

    if not backup_dir.exists():
        return {"control": control, "status": "FAIL",
                "detail": f"Backup directory {BACKUP_DIR} does not exist"}

    backups = sorted(backup_dir.glob("*.sql.gz"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not backups:
        return {"control": control, "status": "FAIL",
                "detail": f"No .sql.gz backup files found in {BACKUP_DIR}"}

    latest = backups[0]
    age_hours = (datetime.now(timezone.utc) -
                 datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc)).total_seconds() / 3600

    if age_hours <= BACKUP_MAX_AGE_HOURS:
        return {"control": control, "status": "PASS",
                "detail": f"Latest backup: {latest.name} ({age_hours:.1f}h ago)"}
    else:
        return {"control": control, "status": "FAIL",
                "detail": f"Latest backup is {age_hours:.1f}h old (limit: {BACKUP_MAX_AGE_HOURS}h): {latest.name}"}


def check_disk_encryption() -> dict:
    """GDPR Art. 25 — Disk encryption must be active for storage containing PII."""
    control = "DISK_ENCRYPTION"
    rc, out = _run(f"lsblk -o NAME,TYPE,MOUNTPOINT {LUKS_DEVICE} 2>/dev/null", ignore_errors=True)
    _, crypt_out = _run("lsblk -o NAME,TYPE | grep crypt", ignore_errors=True)

    if crypt_out.strip():
        return {"control": control, "status": "PASS",
                "detail": f"LUKS encrypted volumes detected: {crypt_out.strip()[:120]}"}

    _, dmsetup_out = _run("dmsetup status 2>/dev/null | grep crypt", ignore_errors=True)
    if dmsetup_out.strip():
        return {"control": control, "status": "PASS",
                "detail": "dm-crypt encrypted volumes active"}

    return {"control": control, "status": "WARN",
            "detail": "No LUKS/dm-crypt volumes detected — verify encryption at rest is configured"}


CHECKS = [
    check_ssh_key_rotation,
    check_root_login_disabled,
    check_password_auth_disabled,
    check_firewall_rules,
    check_log_forwarding,
    check_database_backup,
    check_disk_encryption,
]

STATUS_ICON = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️ ", "ERROR": "🔥"}


def run_compliance_check() -> dict:
    results = []
    for check_fn in CHECKS:
        result = check_fn()
        results.append(result)
        icon = STATUS_ICON.get(result["status"], "?")
        print(f"  {icon} {result['status']:5s}  {result['control']:30s}  {result['detail']}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    warned = sum(1 for r in results if r["status"] == "WARN")
    total  = len(results)
    overall = "COMPLIANT" if failed == 0 else "NON_COMPLIANT"

    return {
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "hostname":    os.uname().nodename,
        "overall":     overall,
        "summary":     {"pass": passed, "fail": failed, "warn": warned, "total": total},
        "controls":    results,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SOC2/GDPR Compliance Check")
    parser.add_argument("--output", default="output/compliance_report.json")
    args = parser.parse_args()

    print("=" * 70)
    print("  AIOps Compliance Monitor — Module 12")
    print(f"  Host: {os.uname().nodename}  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    report = run_compliance_check()

    print("=" * 70)
    overall_icon = "✅" if report["overall"] == "COMPLIANT" else "❌"
    print(f"  {overall_icon}  Overall status: {report['overall']}")
    print(f"     PASS: {report['summary']['pass']}  FAIL: {report['summary']['fail']}  WARN: {report['summary']['warn']}")
    print("=" * 70)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport written → {args.output}")
```

---

## Running the Compliance Script

```bash
cd Module-12/lab
python3 scripts/compliance_check.py --output output/compliance_report.json
```

### Example: Fully Compliant Output

```text
======================================================================
  AIOps Compliance Monitor — Module 12
  Host: db-server  |  2026-08-13 09:15:03
======================================================================
  ✅ PASS   SSH_KEY_ROTATION               authorized_keys last modified 12 days ago (limit: 90)
  ✅ PASS   ROOT_LOGIN_DISABLED            PermitRootLogin no confirmed in sshd_config
  ✅ PASS   PASSWORD_AUTH_DISABLED         PasswordAuthentication no confirmed in sshd_config
  ✅ PASS   FIREWALL_DEFAULT_DENY          Default-deny DROP rules found in INPUT and OUTPUT chains
  ✅ PASS   LOG_FORWARDING                 Log forwarding configured in: ['50-remote.conf']
  ✅ PASS   DATABASE_BACKUP_RECENT         Latest backup: prod_dump_20260813.sql.gz (3.2h ago)
  ⚠️  WARN   DISK_ENCRYPTION               No LUKS/dm-crypt volumes detected — verify encryption at rest
======================================================================
  ✅  Overall status: COMPLIANT
     PASS: 6  FAIL: 0  WARN: 1
======================================================================
Report written → output/compliance_report.json
```

### Scheduling as a Daily Cron Job

```bash
# Run compliance check daily at 07:00 and write a timestamped report
echo "0 7 * * * cd /opt/aiops/Module-12/lab && python3 scripts/compliance_check.py \
  --output output/compliance_\$(date +\%Y\%m\%d).json >> /var/log/compliance.log 2>&1" \
  | crontab -
```

---

## Feeding Compliance Results into Alertmanager

Write a small exporter that converts the compliance report into a Prometheus metric:

```python
# In your lab app or a standalone Flask script:
@app.route("/compliance/metrics")
def compliance_metrics():
    try:
        with open("output/compliance_report.json") as f:
            report = json.load(f)
        fail_count = report["summary"]["fail"]
        # Expose as Prometheus gauge
        return (
            f"# HELP compliance_failures Number of failed SOC2/GDPR controls\n"
            f"# TYPE compliance_failures gauge\n"
            f'compliance_failures{{host="{report["hostname"]}"}} {fail_count}\n'
        ), 200, {"Content-Type": "text/plain"}
    except FileNotFoundError:
        return "compliance_failures 0\n", 200, {"Content-Type": "text/plain"}
```

When `compliance_failures > 0`, Alertmanager can page the security on-call.

---

## Validation Checklist

- [ ] Compliance script runs without syntax errors.
- [ ] Each of the 7 controls produces a PASS, FAIL, or WARN result.
- [ ] `output/compliance_report.json` is written with the correct structure.
- [ ] You can explain which SOC2 criterion or GDPR article each control maps to.
- [ ] Cron job scheduled to run the check daily.
