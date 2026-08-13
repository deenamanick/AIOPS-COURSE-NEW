# Module 12: AIOps Security & Compliance

Welcome to Module 12. Every preceding module in this course focused on keeping systems *available* and *performant*. This module shifts focus to keeping them *secure* and *compliant* — the other dimension of production operations that is equally non-negotiable.

AIOps transforms security operations in the same way it transformed incident management: by automating the detection, correlation, and reporting work that previously required hours of analyst time.

---

## Learning Objectives

By the end of this module, you will be able to:

1. Explain the **Zero Trust** architecture model and implement it with `iptables` rules.
2. Apply **Isolation Forest anomaly detection** (from Module 5) to security data: login times, request rates, and data transfer volumes.
3. Detect **insider threat patterns** by establishing behavioral baselines and alerting on deviation.
4. Correlate security events using the SIEM techniques from Module 8.
5. Write a **Python compliance monitoring script** that checks SSH configuration, firewall rules, log forwarding, and backup schedules.
6. Understand the key requirements of **SOC2 and GDPR** from an infrastructure engineer's perspective.
7. Execute a **Break/Fix activity**: inject a simulated breach, detect it with your compliance script, and remediate.

---

## Prerequisites

- ✅ Modules 1–11 completed
- ✅ Python 3.10+ with `pip` available
- ✅ Docker Engine and Docker Compose v2 installed
- ✅ VirtualBox VMs (`web-server` and `db-server`) from Modules 1–2, running
- ✅ `iptables` available on both VMs (standard on Ubuntu/CentOS)
- ✅ `curl`, `jq`, and `ssh` installed on the host

---

## Lab Architecture

```text
                ┌─────────────────────────────────┐
                │   Zero Trust Network Boundary    │
                │                                  │
   ┌────────┐   │  ┌──────────────┐               │
   │  Host  │──►│  │  web-server  │               │
   └────────┘   │  │  (10.0.2.10) │               │
                │  └──────┬───────┘               │
                │         │ allowed port 5432      │
                │  ┌──────▼───────┐               │
                │  │   db-server  │               │
                │  │  (10.0.2.11) │               │
                │  └──────────────┘               │
                │         ✗ no internet egress     │
                └─────────────────────────────────┘

Security AIOps Pipeline:
  Login events + transfer logs → Isolation Forest → Insider Threat Alert
  Compliance Script → PASS/FAIL Report → Alertmanager notification
```

---

## Lab Setup

```bash
cd Module-12/lab
pip install -r requirements.txt

# Start the security simulation lab app
docker compose up -d --build
```

Open:

- Lab app dashboard: `http://localhost:5003`
- Security metrics: `http://localhost:5003/metrics`
- Compliance reports: `lab/output/` (generated files)

---

## Lessons in this Module

| # | Lesson | What You'll Do |
|---|---|---|
| 01 | [Zero Trust Architecture](./01-zero-trust.md) | Understand the model; configure `iptables` to enforce explicit access |
| 02 | [AIOps Anomaly Detection for Security](./02-security-anomaly-detection.md) | Run Isolation Forest on login + transfer data; inject an insider threat |
| 03 | [SIEM Correlation & Insider Threat](./03-siem-correlation.md) | Correlate security events across sources using Module 8 techniques |
| 04 | [Compliance Monitoring Script](./04-compliance-monitoring.md) | Write a Python script that generates a SOC2/GDPR compliance report |
| 05 | [Break/Fix: Simulated Breach](./05-break-fix.md) | Inject violations → detect → remediate → verify |

Start with **01-zero-trust.md**.
