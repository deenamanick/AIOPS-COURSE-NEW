# 01 — Markov Chain Theory for AIOps

Every system passes through states. A healthy database becomes degraded under load, then critical when connections exhaust, then failed when it stops responding. The key insight is: **the probability of transitioning to the next state depends primarily on the current state, not the full history.** This is the Markov property, and it makes state prediction computationally tractable.

---

## Why Markov Chains for Infrastructure?

Module 9 used **linear regression** to predict when a metric (disk, CPU) would reach capacity. That works for steady growth. But many infrastructure failures don't follow linear growth—they follow **state transitions**:

| Pattern | Linear Regression | Markov Chain |
|---|---|---|
| Steady disk fill | ✅ Excellent | ⚠️ Overkill |
| CPU spike → memory pressure → OOM | ❌ Not a linear pattern | ✅ Models state cascade |
| Healthy → Degraded → Critical → Failed | ❌ Not a numeric trend | ✅ Captures transition probabilities |
| Intermittent flapping (Healthy ↔ Degraded) | ❌ Averages out the signal | ✅ Captures oscillation probability |

Linear regression answers: **"When will this number reach a limit?"**
Markov chains answer: **"Given the current state, what's the probability of failure in the next N time steps?"**

---

## The Four States

For this module, we define four discrete operational states:

```text
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Healthy  │───►│ Degraded │───►│ Critical │───►│  Failed  │
│          │◄───│          │◄───│          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     ▲                                               │
     └───────────────────────────────────────────────┘
                    (after recovery)
```

| State | Definition | Example Indicators |
|---|---|---|
| **Healthy** | All metrics normal, SLOs met | CPU < 60%, mem < 60%, error_rate < 5% |
| **Degraded** | Performance reduced, SLOs at risk | CPU 60–80%, mem 60–80%, latency rising |
| **Critical** | Near failure, SLOs breached | CPU > 80%, mem > 80%, error_rate > 20% |
| **Failed** | Service down, user impact | error_rate > 50%, service unresponsive |

The thresholds are configurable. What matters is that you map continuous metrics to discrete states consistently.

---

## The Markov Property

A Markov chain has the **memoryless** property:

```text
P(next state | current state, all previous states) = P(next state | current state)
```

In plain language: the probability of transitioning from Critical to Failed depends only on the fact that you're currently Critical—not on how you got there, or how long you've been there.

Is this perfectly true for infrastructure? No. A system that has been Critical for 30 minutes is more likely to fail than one that just entered Critical. But as an approximation, it's remarkably useful and computationally simple.

---

## Transition Probabilities

A transition probability is the chance of moving from one state to another in one time step:

```text
P(Healthy → Healthy)  = 0.85   (85% chance of staying healthy)
P(Healthy → Degraded) = 0.12   (12% chance of degrading)
P(Healthy → Critical) = 0.02   (2% chance of jumping to critical)
P(Healthy → Failed)   = 0.01   (1% chance of direct failure)
```

Each row sums to 1.0 (the system must be in some state):

```text
0.85 + 0.12 + 0.02 + 0.01 = 1.00  ✅
```

---

## The Transition Matrix

All transition probabilities are organized into a matrix **P**:

```text
              To:
           H     D     C     F
From: H [ 0.85  0.12  0.02  0.01 ]
      D [ 0.15  0.60  0.20  0.05 ]
      C [ 0.05  0.10  0.55  0.30 ]
      F [ 0.10  0.05  0.05  0.80 ]
```

Reading row by row:
- From **Healthy**: 85% stay, 12% degrade, 2% go critical, 1% fail directly
- From **Degraded**: 15% recover, 60% stay degraded, 20% go critical, 5% fail
- From **Critical**: 5% recover fully, 10% improve to degraded, 55% stay critical, 30% fail
- From **Failed**: 10% recover (auto-remediation), 5% partial, 5% stay critical, 80% remain failed

---

## N-Step Prediction

To predict the state distribution after N time steps, multiply the initial state vector by the matrix N times:

```text
state_vector(t + N) = state_vector(t) × P^N
```

Example: if the system is currently **Critical** (state vector = `[0, 0, 1, 0]`):

```text
After 1 step:  [0, 0, 1, 0] × P   = [0.05, 0.10, 0.55, 0.30]  → 30% failure
After 2 steps: [0, 0, 1, 0] × P²  = [0.06, 0.11, 0.39, 0.44]  → 44% failure
After 6 steps: [0, 0, 1, 0] × P⁶  ≈ [0.10, 0.12, 0.17, 0.61]  → 61% failure ⚠️
```

If each step represents 5 minutes, then 6 steps = 30 minutes. At 61% failure probability, we cross the 60% threshold and trigger remediation.

---

## Connection to Module 10 (Auto-Remediation)

In Module 10, you built Ansible playbooks and webhook-triggered healing:

```text
Module 13 Forecast:  P(Failed | Critical, 30 min) = 61% > 60%
         │
         ▼
   Webhook POST ──► Module 10 Flask Endpoint ──► Ansible Playbook
                                                      │
                                                      ▼
                                              restart-service.yml
                                              clear-logs.yml
                                              scale-up.yml
```

The Markov model provides the **trigger signal**. Module 10 provides the **action**. Together, they form a complete predictive auto-remediation pipeline.

---

## Key Formulas

| Concept | Formula |
|---|---|
| Transition probability | `P(j|i) = count(i→j) / count(i→*)` |
| Matrix normalization | Each row sums to 1.0 |
| N-step prediction | `v(t+N) = v(t) × P^N` |
| Failure probability | `P(Failed) = v(t+N)[Failed_index]` |
| Threshold check | `if P(Failed) >= 0.60: trigger_webhook()` |

---

## Lab Preview

In the following lessons, you will:

1. Generate 30 days of synthetic state data from realistic metric patterns.
2. Count transitions and build the probability matrix.
3. Visualize the matrix as a heatmap.
4. Run N-step forecasts from any starting state.
5. Wire the forecast to a webhook that triggers Ansible remediation.
6. Run a live drill where you inject load and watch the model predict and prevent failure.

---

## Key Takeaway

Linear regression predicts **when a number hits a limit**. Markov chains predict **what state the system will be in**. For cascading failures—where one degradation leads to another—Markov chains capture the dynamics that linear models miss. In the next lesson, you'll start by collecting the data that feeds the model.
