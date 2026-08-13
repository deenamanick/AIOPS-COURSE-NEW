# Module 13: Advanced Predictive Analysis — Markov Chains

Welcome to Module 13! In Module 12, you applied AIOps techniques to security—detecting behavioral anomalies, enforcing Zero Trust, and automating compliance checks. Security tells you **who** is doing something unusual. This module teaches you to predict **what will happen next** using Markov chain models that forecast system state transitions and trigger automated prevention before failures occur.

---

## Learning Objectives

By the end of this module, you will be able to:

1. Explain the **Markov property** (memoryless transitions) and why it applies to infrastructure state modeling.
2. Map raw infrastructure metrics to discrete states: **Healthy → Degraded → Critical → Failed**.
3. Build a **state transition matrix** from historical state data and interpret the probabilities.
4. Use **N-step matrix exponentiation** to predict failure probability within a configurable time horizon.
5. Trigger a **webhook to an Ansible playbook** when the predicted failure probability exceeds a threshold.
6. Run a full **break/fix drill**: inject load, watch the model calculate rising failure probability, and observe automated remediation.

---

## Prerequisites

- ✅ Module 12 completed
- ✅ Python 3.10+ with `pip` available
- ✅ Docker Engine and Docker Compose v2 installed
- ✅ Familiarity with NumPy arrays and matrix operations (basic)
- ✅ Understanding of Ansible playbooks (Module 10)
- ✅ At least 4 GB RAM available

---

## Lab Architecture

```text
Historical Metrics ──► State Mapper ──► State Log (CSV)
(CPU, mem, disk,           │                  │
 error_rate)               │                  ▼
                           │         Transition Counter
                           │                  │
                           │                  ▼
                           │         Transition Matrix (CSV)
                           │                  │
                           ▼                  ▼
                    Live Flask App ──► Markov Forecaster
                    (state simulation)        │
                         │              ┌─────┴──────┐
                         │              ▼            ▼
                         │         P(Failed)    P(Failed)
                         │          < 60%        ≥ 60%
                         │            │            │
                         │            ▼            ▼
                         │         ✅ OK      ⚠️ Webhook
                         │                   ──► Ansible
                         │                       Playbook
                         ▼
                    Prometheus Gauges
                    (state, probability)
```

---

## Lab Setup

```bash
cd Module-13/lab
pip install -r requirements.txt
docker compose up -d --build
```

Open:

- Markov lab service: `http://localhost:5002`
- State API: `http://localhost:5002/api/state`
- Transition matrix API: `http://localhost:5002/api/matrix`
- Prometheus metrics: `http://localhost:5002/metrics`
- Forecast outputs: `lab/output/` (generated plots and matrices)

---

## Lessons in this Module

| # | Lesson | What You'll Do |
|---|---|---|
| 01 | [Markov Chain Theory for AIOps](./01-markov-theory.md) | Understand the math behind state transition modeling and why it works for infrastructure |
| 02 | [Data Collection & Baselines](./02-data-collection-baselines.md) | Generate historical metrics, map to discrete states, produce a state log |
| 03 | [Markov State Modeling](./03-markov-state-modeling.md) | Build a transition matrix from the state log and interpret the probabilities |
| 04 | [Predictive Forecasting & Automation](./04-predictive-forecasting.md) | Compute N-step failure probability and trigger webhook remediation |
| 05 | [Break/Fix: Markov Prediction Drill](./05-break-fix-markov.md) | Inject load, watch the model predict failure, observe automated remediation |
| 06 | [Production Patterns & Deliverables](./06-bonus-deliverables.md) | Advanced Markov variants, cross-module integration, and evidence submission |

Start with **01-markov-theory.md**.
