# 05 — Break/Fix: Simulated Security Breach

This is the practical capstone of Module 12. You will deliberately introduce security violations on `db-server`, run your compliance script to detect them, fix each violation, and verify that the script returns to a clean state.

This exercise mirrors what a penetration tester leaves behind — and what your automated compliance monitoring must catch.

---

## Scenario

The security operations team has received an anonymous tip that someone with insider access may have tampered with `db-server`. Your job:

1. **Simulate** the breach by introducing four violations.
2. **Detect** all violations using your compliance script.
3. **Remediate** each one, explaining the business risk it posed.
4. **Verify** the compliance script shows zero failures.

---

## Phase 1: Simulate the Breach

SSH into `db-server`:

```bash
ssh user@10.0.2.11
```

### Violation 1: Open an Unauthorized Port

An attacker opened port `4444` to create a reverse shell listener:

```bash
# Open port 4444 — simulates a rogue process listening for connections
sudo iptables -I INPUT -p tcp --dport 4444 -j ACCEPT

# Verify the rule was inserted
sudo iptables -L INPUT -n -v --line-numbers | grep 4444
```

Expected:

```text
1   ACCEPT   tcp  --  anywhere  anywhere   tcp dpt:4444
```

### Violation 2: Create a Rogue SSH Key

An attacker added their own public key to gain persistent access even after their initial vector is closed:

```bash
# Create a fake rogue key (in a real attack this would be their actual public key)
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC0bW... attacker@evil.com" \
  >> /root/.ssh/authorized_keys

echo "Rogue key appended. Verify:"
wc -l /root/.ssh/authorized_keys
```

### Violation 3: Re-enable Root Login via SSH

The attacker re-enabled root login so they can connect directly as root:

```bash
sudo sed -i 's/^PermitRootLogin no/PermitRootLogin yes/' /etc/ssh/sshd_config

# Verify the change
grep PermitRootLogin /etc/ssh/sshd_config
```

Expected:

```text
PermitRootLogin yes
```

### Violation 4: Disable Log Forwarding

The attacker disabled log forwarding to the SIEM to erase their tracks:

```bash
# Rename the rsyslog forwarding config so it is no longer loaded
sudo mv /etc/rsyslog.d/50-remote.conf /etc/rsyslog.d/50-remote.conf.disabled

# Restart rsyslog so the change takes effect
sudo systemctl restart rsyslog

echo "Log forwarding disabled."
```

---

## Phase 2: Detect — Run the Compliance Script

From your host machine (or inside the lab container):

```bash
cd Module-12/lab
python3 scripts/compliance_check.py --output output/breach_report.json
```

**Expected output — 4 failures:**

```text
======================================================================
  AIOps Compliance Monitor — Module 12
  Host: db-server  |  2026-08-13 10:42:17
======================================================================
  ⚠️  WARN   SSH_KEY_ROTATION               authorized_keys last modified 0 days ago (recently changed)
  ❌ FAIL   ROOT_LOGIN_DISABLED            Root login not disabled: 'PermitRootLogin yes'
  ✅ PASS   PASSWORD_AUTH_DISABLED         PasswordAuthentication no confirmed in sshd_config
  ❌ FAIL   FIREWALL_DEFAULT_DENY          INPUT chain has a non-DROP rule inserted at position 1
  ❌ FAIL   LOG_FORWARDING                 No forwarding (@@) rules found in /etc/rsyslog.d/*.conf
  ✅ PASS   DATABASE_BACKUP_RECENT         Latest backup: prod_dump_20260813.sql.gz (4.1h ago)
  ⚠️  WARN   DISK_ENCRYPTION               No LUKS/dm-crypt volumes detected
======================================================================
  ❌  Overall status: NON_COMPLIANT
     PASS: 2  FAIL: 3  WARN: 2
======================================================================
Report written → output/breach_report.json
```

The script detected 3 direct failures and 1 warning. Note: the `SSH_KEY_ROTATION` check shows `WARN` because the `authorized_keys` modification timestamp was updated when the rogue key was appended — an indirect indicator of the key injection.

---

## Phase 3: Remediate Each Violation

### Fix 1: Remove the Unauthorized iptables Rule

```bash
# List rules with line numbers to find the rogue rule
sudo iptables -L INPUT -n -v --line-numbers

# Remove the rule at line 1 (the port 4444 ACCEPT rule)
sudo iptables -D INPUT 1

# Verify it is gone
sudo iptables -L INPUT -n | grep 4444
# (no output expected)

# Persist the corrected ruleset
sudo netfilter-persistent save
```

**Business risk it posed**: An open port 4444 allows any internet host to connect to a listener on `db-server`. In a real breach, this would be a reverse shell giving the attacker an interactive terminal inside the Zero Trust boundary.

### Fix 2: Remove the Rogue SSH Key

```bash
# View all keys in authorized_keys
cat -n /root/.ssh/authorized_keys

# Remove the last line (the rogue key)
# In production: manually verify each key belongs to a known employee
sudo sed -i '/attacker@evil.com/d' /root/.ssh/authorized_keys

# Verify only legitimate keys remain
wc -l /root/.ssh/authorized_keys
```

**Best practice**: In production, SSH public keys should be managed by a configuration management tool (Ansible, Chef) so that any manually added keys are detected and removed on the next configuration run.

**Business risk it posed**: The rogue key gives the attacker persistent SSH access. Even if their initial vulnerability is patched, they retain access until the key is removed.

### Fix 3: Disable Root Login

```bash
sudo sed -i 's/^PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Verify
grep PermitRootLogin /etc/ssh/sshd_config
# PermitRootLogin no

# Reload SSH daemon
sudo systemctl reload sshd
```

**Business risk it posed**: Root login allows any attacker who has a valid SSH key to log in with the most privileged account on the system, bypassing the need to escalate from a regular user — eliminating one entire layer of defence.

### Fix 4: Re-enable Log Forwarding

```bash
sudo mv /etc/rsyslog.d/50-remote.conf.disabled /etc/rsyslog.d/50-remote.conf

# Restart rsyslog
sudo systemctl restart rsyslog

# Verify forwarding is active
sudo systemctl status rsyslog
```

**Business risk it posed**: Without log forwarding, all attacker activity on `db-server` is invisible to the SIEM. The attacker can delete local logs (`/var/log/auth.log`) to erase all evidence. Log forwarding to a remote, write-protected SIEM is a core non-repudiation control required by both SOC2 CC7.2 and GDPR Art. 33.

---

## Phase 4: Verify — Re-run the Compliance Script

```bash
python3 scripts/compliance_check.py --output output/remediation_report.json
```

**Expected output — clean:**

```text
======================================================================
  AIOps Compliance Monitor — Module 12
  Host: db-server  |  2026-08-13 11:05:44
======================================================================
  ✅ PASS   SSH_KEY_ROTATION               authorized_keys last modified 0 days ago (limit: 90)
  ✅ PASS   ROOT_LOGIN_DISABLED            PermitRootLogin no confirmed in sshd_config
  ✅ PASS   PASSWORD_AUTH_DISABLED         PasswordAuthentication no confirmed in sshd_config
  ✅ PASS   FIREWALL_DEFAULT_DENY          Default-deny DROP rules found in INPUT and OUTPUT chains
  ✅ PASS   LOG_FORWARDING                 Log forwarding configured in: ['50-remote.conf']
  ✅ PASS   DATABASE_BACKUP_RECENT         Latest backup: prod_dump_20260813.sql.gz (4.8h ago)
  ⚠️  WARN   DISK_ENCRYPTION               No LUKS/dm-crypt volumes detected
======================================================================
  ✅  Overall status: COMPLIANT
     PASS: 6  FAIL: 0  WARN: 1
======================================================================
Report written → output/remediation_report.json
```

Zero failures. The `DISK_ENCRYPTION` warning remains because VirtualBox VMs do not use LUKS by default — this is expected in the lab environment.

---

## Incident Timeline: What the Audit Trail Shows

After remediating, write a brief incident timeline — this is the artifact a SOC2 auditor would request if this were a real breach:

| Time | Event | Source |
|---|---|---|
| 02:03 | `bob` logged in from 203.0.113.42 | `auth.log` |
| 02:04 | `/root/.ssh/authorized_keys` modified | File audit |
| 02:05 | `/etc/ssh/sshd_config` modified | File audit |
| 02:06 | `sshd` reloaded | `systemd` journal |
| 02:07 | `rsyslog` stopped | `systemd` journal |
| 02:08 | 4.3 GB egress to 203.0.113.42 | Network monitor |
| 02:14 | SIEM lost contact with `db-server` log stream | SIEM alert |
| 07:00 | Compliance script flagged 3 FAIL | Compliance cron |
| 07:02 | Automated alert paged security on-call | Alertmanager |

Note that the log forwarding disruption (02:07) created a gap in the SIEM visibility — exactly as the attacker intended. This is why the SIEM alert on *loss of log stream* is as important as alerts on anomalous *content* of logs.

---

## Module 12 Summary

You have now built a complete AIOps security and compliance stack:

| Capability | Tool / Technique |
|---|---|
| Network micro-segmentation | `iptables` Zero Trust rules |
| Behavioral anomaly detection | Isolation Forest on user activity data |
| Multi-source event correlation | SIEM sliding-window correlation rules |
| Continuous compliance monitoring | Python compliance script with 7 controls |
| Automated breach detection | Compliance cron + Alertmanager integration |

---

## Validation Checklist

- [ ] All 4 violations introduced on `db-server`.
- [ ] Compliance script detects exactly 3 FAIL results with violations active.
- [ ] Each violation remediated in the correct order.
- [ ] Compliance script shows 0 FAIL results after remediation.
- [ ] You can articulate the business risk each violation posed.
- [ ] Incident timeline written covering the full attacker session.
