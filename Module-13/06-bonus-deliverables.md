# 06 — Production Patterns & Deliverables

This lesson covers advanced Markov model variants, production deployment considerations, cross-module integration, and the evidence you should submit to demonstrate Module 13 mastery.

---

## Advanced Markov Variants

### Higher-Order Markov Chains

A standard (first-order) Markov chain considers only the current state. A **second-order** chain considers the last two states:

```text
P(next | current, previous) ≠ P(next | current)
```

Example: `P(Failed | Critical, Degraded)` might be higher than `P(Failed | Critical, Healthy)` because the system has been trending downward.

Implementation: expand the state space to pairs:

```text
States: (Healthy,Healthy), (Healthy,Degraded), (Degraded,Critical), ...
Matrix: 16×16 instead of 4×4
```

Trade-off: more accurate but requires much more data to estimate 256 transition probabilities reliably.

### Hidden Markov Models (HMMs)

In a **Hidden Markov Model**, the true state is not directly observable. You observe **emissions** (metrics) that probabilistically indicate the hidden state:

```text
Hidden state:  Healthy ──► Degraded ──► Critical
Observations:  CPU=35%     CPU=68%      CPU=72%
```

CPU at 72% could mean Degraded or Critical—the observation is ambiguous. HMMs use the **Viterbi algorithm** to infer the most likely sequence of hidden states.

HMMs are more powerful but significantly more complex. For this course, the direct state mapping approach (Lesson 02) is sufficient.

### Continuous-Time Markov Chains (CTMCs)

Our model uses discrete time steps (every 5 minutes). A **CTMC** models transitions that can occur at any moment, using transition **rates** instead of probabilities.

CTMCs are mathematically elegant but harder to estimate from data. They're used in advanced capacity planning and queuing theory.

---

## Production Deployment Considerations

### Data Quality

| Factor | Training (This Module) | Production |
|---|---|---|
| Data source | Synthetic CSV | Prometheus / Loki / real metrics |
| Volume | 720 data points (30 days) | Millions of data points |
| State mapping | Static thresholds | SLO-based or ML-based |
| Update frequency | One-time build | Retrain weekly or on drift detection |

### Model Staleness

Transition probabilities change as your infrastructure evolves:
- New services added → different failure patterns
- Better remediation → higher recovery probabilities
- Traffic growth → more frequent degradation

**Recommendation**: rebuild the transition matrix weekly from the last 30 days of data. Compare the new matrix to the old one—if any probability changes by more than 10%, investigate.

### Per-Component Models

Instead of one global model, build separate transition matrices for each critical component:

```text
web-server:    P_web (4×4 matrix)
app-server:    P_app (4×4 matrix)
db-server:     P_db  (4×4 matrix)
load-balancer: P_lb  (4×4 matrix)
```

Each component has different failure characteristics. A database might have high Critical → Failed probability due to connection pool exhaustion, while a web server might recover more easily.

### Threshold Tuning

| Threshold | Effect |
|---|---|
| 40% | Aggressive — many false alarms, but catches everything |
| 60% | Balanced — our default |
| 80% | Conservative — fewer alerts, but might miss fast failures |

Start at 60%, monitor for one month, then adjust based on:
- **False positive rate**: webhook triggered but no failure would have occurred
- **False negative rate**: failure occurred but webhook wasn't triggered

---

## Cross-Module Integration Summary

Module 13 ties together concepts from across the entire course:

| Module | Concept Used in Module 13 |
|---|---|
| Module 1 | AIOps lifecycle: collect → observe → detect → predict → automate |
| Module 2 | Data processing and AI-driven analysis patterns |
| Module 5 | Anomaly detection feeds state classification |
| Module 6 | Prometheus metrics provide the raw data for state mapping |
| Module 7 | SLOs define what "Healthy" vs "Degraded" means |
| Module 8 | Correlation engine identifies which component is degrading |
| Module 9 | Time-series forecasting (complementary to Markov prediction) |
| Module 10 | Ansible playbooks execute the remediation triggered by the webhook |
| Module 11 | Local LLMs could generate natural-language explanations of state transitions |
| Module 12 | Security state monitoring can use the same Markov framework |

---

## Full AIOps Maturity Mapping

```text
Level 1 — Reactive (Modules 1–3):
  Build the lab, deploy apps, set up monitoring.

Level 2 — Proactive (Modules 4–7):
  CI/CD, anomaly detection, alerting, SLOs.

Level 3 — Predictive (Modules 8–9, 13):
  Correlation, forecasting, Markov chains.

Level 4 — Autonomous (Modules 10–12):
  Auto-remediation, chaos engineering, security automation.
```

Module 13 is the culmination of Level 3: you can now predict not just when a number will hit a limit (Module 9), but what state the system will transition to (Module 13) and automatically prevent failure (Module 10).

---

## Deliverables Checklist

Submit the following evidence to demonstrate Module 13 completion:

### Required Files

- [ ] `data/raw_metrics.csv` — 30 days of generated metrics (720 rows)
- [ ] `data/state_log.csv` — metrics mapped to discrete states
- [ ] `data/transition_matrix.csv` — 4×4 probability matrix
- [ ] `output/transition_heatmap.png` — visual heatmap of the matrix
- [ ] **Break/Fix report** — timeline, prediction accuracy, remediation outcome

### Required Screenshots

- [ ] Terminal output of `build_transition_matrix.py` showing the matrix
- [ ] Terminal output of `forecast.py` showing threshold exceeded
- [ ] Docker logs showing state transitions during the drill
- [ ] System returning to Healthy after remediation

### Knowledge Questions

Answer these in your report:

1. Why is the Markov property a reasonable approximation for infrastructure state modeling?
2. What would happen if the Failed state had `P(Failed → Failed) = 1.0` (absorbing state)?
3. How would you tune the threshold if you're getting too many false alarms?
4. When would you use linear regression (Module 9) vs Markov chains (Module 13)?
5. How often should you retrain the transition matrix in production?

---

## Next Steps

You have now completed all 13 modules of the AIOps course. You can:

1. **Extend Module 13**: implement per-component Markov models for your lab environment.
2. **Integrate with Module 11**: feed Markov predictions to a local LLM for natural-language incident forecasts.
3. **Build a dashboard**: create a Grafana panel that shows the current Markov failure probability in real time.
4. **Run a full capstone**: combine Modules 5–13 into an end-to-end pipeline that detects anomalies, predicts state transitions, and auto-remediates.

Congratulations on completing the AIOps course! 🎉
