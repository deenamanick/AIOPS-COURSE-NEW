# Module 10: Auto-Remediation & Self-Healing

Welcome to Module 10! In Module 9, you learned to forecast resource exhaustion using linear regression, build composite risk scores, and set predictive alerts that fire before failures happen. Prediction tells you that something **will** break. This module teaches the next step: **automatically fixing it** before a human ever gets paged.

---

## Learning Objectives

By the end of this module, you will be able to:

1. Write **Ansible playbooks** for the three most common remediation tasks: service restart, log cleanup, and container scaling.
2. Configure **Alertmanager webhooks** that trigger Ansible remediation automatically when an alert fires.
3. Practice **chaos engineering** with three controlled experiments: process kill, network partition, and resource starvation.
4. Implement **feature flag rollback** that disables a feature automatically when anomaly detection fires.
5. Understand **GitOps principles** and when to keep a human in the loop instead of automating.

---

## Prerequisites

- ✅ Module 9 completed
- ✅ Python 3.10+ with `pip` available
- ✅ Docker Engine and Docker Compose v2 installed
- ✅ Ansible installed (`pip install ansible` or `apt install ansible`)
- ✅ Familiarity with Flask, Prometheus, and Alertmanager (Modules 6–7)
- ✅ At least 4 GB RAM available

---

## Lab Architecture

```text
Alert Fires (Alertmanager)
        │
        ▼
  Webhook Receiver (Flask)
        │
        ├──► Validate alert severity & type
        │
        ├──► Run Ansible Playbook
        │         │
        │         ├── restart-service.yml   ← Nginx crashed
        │         ├── clear-logs.yml        ← Disk > 85%
        │         └── scale-up.yml          ← High load
        │
        ├──► Verify remediation worked
        │
        ├──► Rollback if verify fails
        │
        └──► Log result (success / failure / rolled-back)

Chaos Engineering Lab:
  Kill process → Load balancer reroutes → TTD / TTR measured
  Network partition → App degrades gracefully → Circuit breaker fires
  CPU stress → Alerts fire → Auto-scaling kicks in

Feature Flag System:
  Anomaly detected → POST /flags/rollback → Feature disabled → System recovers
```

---

## Lab Setup

```bash
cd Module-10/lab
pip install -r requirements.txt
pip install ansible
docker compose up -d --build
```

Open:

- Webhook receiver: `http://localhost:5001`
- Feature flag API: `http://localhost:5001/flags`
- Remediation log: `http://localhost:5001/api/remediation-log`
- Chaos experiment control: `http://localhost:5001/chaos`

---

## Lessons in this Module

| # | Lesson | What You'll Do |
|---|---|---|
| 01 | [Self-Healing Patterns](./01-self-healing-patterns.md) | Learn the Detect → Validate → Act → Verify → Rollback → Log cycle |
| 02 | [Ansible Playbook Lab](./02-ansible-playbooks.md) | Write and run 3 playbooks: restart, log cleanup, and scale-up |
| 03 | [Webhook-Triggered Healing](./03-webhook-healing.md) | Wire Alertmanager → Flask webhook → Ansible end-to-end |
| 04 | [Chaos Engineering](./04-chaos-engineering.md) | Run 3 chaos experiments and measure TTD and TTR |
| 05 | [Feature Flags & Auto-Rollback](./05-feature-flags-rollback.md) | Toggle features via flags and auto-rollback on anomaly |
| 06 | [GitOps & Production Patterns](./06-gitops-production.md) | GitOps principles, human-in-the-loop policies, and deliverables |

Start with **01-self-healing-patterns.md**.
