# 06 — Course Wrap-Up & Deliverables

You have completed all 11 modules of the AIOps course. This final lesson consolidates what you built, lists your deliverables, maps each capability to production use cases, and points you to the next steps in your AIOps career.

---

## What You Built: The Full AIOps Stack

```text
Module  1  Environment Setup       →  Prometheus, Grafana, Docker Compose baseline
Module  2  LLM Foundations         →  OpenAI API, prompt engineering, AI for ops
Module  3  Telemetry & Metrics     →  Instrumented services, PromQL, custom gauges
Module  4  Log Analytics           →  Structured logging, log parsing, log-to-metric
Module  5  Anomaly Detection       →  Z-score, IQR, EWMA, composite anomaly scores
Module  6  Smart Alerting          →  Alert fatigue, Alertmanager routing, silence windows
Module  7  SRE & SLOs              →  Error budgets, SLI/SLO/SLA, burn-rate alerting
Module  8  Incident Correlation    →  Cascading failure analysis, root alert identification
Module  9  Predictive Maintenance  →  Linear regression forecasting, DORA metrics
Module 10  Auto-Remediation        →  Ansible playbooks, webhook healing, chaos engineering
Module 11  Local LLMs & Capstone   →  Ollama, LLM RCA, blameless post-mortems, capstone
```

Every module's lab produced a working system. Together, they form a complete AIOps pipeline:

```text
Instrument → Collect → Store → Alert → Detect → Correlate → Forecast
     → Remediate → Analyse → Document → Learn → Improve
```

---

## Module 11 Deliverables

### Deliverable 1: Ollama Setup Evidence

Submit:
- `ollama list` output showing the model is installed
- The response to the connection pool question from the interactive test
- One observation about response quality compared to Module 2's cloud API

### Deliverable 2: LLM Incident Report

Submit `output/rca_report.md`:
- The full generated RCA with all six sections populated
- Your quality review scores on the five criteria (accuracy, completeness, actionability, hallucination check, causality)
- One sentence on what the LLM got right and one on what it missed or got wrong

### Deliverable 3: Blameless Post-Mortem

Submit `output/capstone-post-mortem.md`:
- All sections complete — no "N/A" in the Timeline or Action Items sections
- The 5 Whys analysis showing how you arrived at the root cause
- At least 3 action items with owners and due dates

### Deliverable 4: AIOps Maturity Self-Assessment

Submit:
- Your score card (all six dimensions rated 1–4)
- Your current overall maturity level
- Your Level 2→3 roadmap (which 3 services, which 5 steps first, target date)

### Deliverable 5: Capstone Summary

Submit the output of `capstone_summary.py`:
- All 8 steps showing ✅
- TTD and TTR recorded
- Screenshot or log of the LLM RCA generation (showing model name and duration)

---

## Connecting AIOps to Real Production Environments

| What You Built in the Lab | Production Equivalent |
|---|---|
| Prometheus + Grafana | Datadog, New Relic, Dynatrace, or self-hosted Prometheus |
| Ollama + local LLM | OpenAI enterprise, Anthropic Claude, or on-prem GPU cluster |
| Ansible playbooks | Ansible AWX, AWS Systems Manager, Google Cloud Runbook Automation |
| Alertmanager webhooks | PagerDuty, OpsGenie, or custom webhook receivers |
| Feature flags | LaunchDarkly, Unleash, AWS AppConfig, or custom |
| GitOps (ArgoCD/Flux) | ArgoCD in production Kubernetes clusters |
| Chaos engineering | Chaos Monkey, Gremlin, LitmusChaos, or AWS Fault Injection Simulator |
| Post-mortems | Atlassian Confluence, Notion, PagerDuty Postmortems |

The patterns are identical — only the product names change.

---

## What is Not Covered (Next Steps)

This course focused on the operations layer. The following are natural next steps:

| Topic | What to Learn Next |
|---|---|
| **ML-based anomaly detection** | Isolation Forest, LSTM autoencoders for multi-variate anomaly detection |
| **Distributed tracing** | OpenTelemetry, Jaeger, Tempo — trace requests across services |
| **eBPF observability** | Cilium, Pixie — kernel-level observability without instrumentation |
| **AIOps at scale** | Elasticsearch, Apache Kafka for high-volume log pipelines |
| **LLM fine-tuning** | Fine-tune a model on your own runbooks and incident history |
| **AI-assisted capacity planning** | Prophet, NeuralProphet for seasonal traffic forecasting |
| **Kubernetes-native AIOps** | Kubernetes events, HPA, KEDA, and Kubernetes-aware alerting |

---

## The AIOps Engineer's Mindset

Three principles to carry forward:

### 1. Automate the repetitive, not the novel
Auto-remediation works for the 20% of incidents that account for 80% of your pages. The other 80% require human judgment — cascading failures, data integrity issues, security incidents, novel failures. Keep humans in the loop for those.

### 2. Every outage is a system failure
The engineer who made the mistake was enabled by a system with missing checks, absent alerts, or unclear runbooks. Fix the system. The post-mortem action items are the most valuable artifact of any incident.

### 3. Measure what matters
TTD, TTR, deployment frequency, change failure rate, error budget consumption — these are the numbers that tell you whether your AIOps investment is working. Dashboards that nobody reads are not monitoring; they are theatre.

---

## Course Summary

```text
You started with a blank VM and a lab environment.

You ended with:
  - A fully instrumented service with Prometheus metrics and structured logs
  - An anomaly detection engine with composite scoring
  - SLO-based alerting with error budgets
  - Cascading failure correlation
  - Predictive capacity forecasting
  - Automated remediation via Ansible and webhook integration
  - Chaos engineering experiments with TTD/TTR measurement
  - A local LLM that generates incident RCA reports without cloud APIs
  - A blameless post-mortem for every incident
  - An AIOps maturity assessment and roadmap

You are now an AIOps engineer.
```

---

## Final Checklist

- [ ] All five Module 11 deliverables submitted.
- [ ] Capstone completed with all 8 steps ✅.
- [ ] Post-mortem written, reviewed, and action items tracked.
- [ ] AIOps maturity level self-assessed; roadmap written.
- [ ] At least one next-steps topic identified for continued learning.
