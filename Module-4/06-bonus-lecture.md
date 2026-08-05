# 06 — DORA Metrics, Deployment Strategies & Deliverables

Congratulations on completing the core lab components of Module 4! Before you submit your deliverables, let's explore the frameworks that elite engineering organizations use to measure velocity, manage risk, and deploy safely at scale.

---

## 1. DORA Metrics — Measuring Engineering Performance

The **DORA (DevOps Research and Assessment)** metrics are four key indicators that measure the performance of a software delivery team. They were identified through years of research by Google's DORA team (now part of Google Cloud).

| Metric | Definition | Elite Performance | Low Performance |
|---|---|---|---|
| **Deployment Frequency** | How often code is deployed to production. | On-demand (multiple times per day) | Between once per month and once every 6 months |
| **Lead Time for Changes** | Time from code commit to code running in production. | Less than one day | Between one month and six months |
| **Change Failure Rate (CFR)** | Percentage of deployments that cause a failure in production. | 0–15% | 46–60% |
| **Mean Time to Recovery (MTTR)** | How long it takes to recover from a production failure. | Less than one hour | Between one week and one month |

### How Your Pipeline Maps to DORA

| DORA Metric | How Your Module 4 Pipeline Contributes |
|---|---|
| Deployment Frequency | GitHub Actions deploys automatically on every merge to `main` → enables on-demand deployment. |
| Lead Time for Changes | Automated lint → test → build → deploy means no manual gates (except the optional approval step). |
| Change Failure Rate | The 5 automated tests (including the golden dataset test) catch broken code before it reaches production. |
| Mean Time to Recovery | Kubernetes rolling updates + self-healing + HPA ensure rapid recovery from failures. |

---

## 2. Deployment Strategies

So far, you've been using Kubernetes' default deployment strategy: **Rolling Update**. But production teams use several strategies depending on their risk tolerance.

### Rolling Update (Default)

```
  Time ──────────────────────────────────────►

  Pod 1 (v1) ████████████░░░░░░░░░░░░░░░░░░░░
  Pod 2 (v1) ████████████████████░░░░░░░░░░░░
  Pod 1 (v2) ░░░░░░░░░░░░████████████████████
  Pod 2 (v2) ░░░░░░░░░░░░░░░░░░░░████████████

  █ = Running    ░ = Not running
```

- Pods are replaced one at a time.
- At any moment, both old and new versions may be running simultaneously.
- **Zero downtime** but potential version inconsistency during the transition.
- **Best for:** Most deployments. Low risk, no extra infrastructure required.

### Blue-Green Deployment

```
  ┌────────────────────┐    ┌────────────────────┐
  │    BLUE (v1)       │    │    GREEN (v2)       │
  │   ┌─────┐ ┌─────┐ │    │   ┌─────┐ ┌─────┐  │
  │   │Pod 1│ │Pod 2│ │    │   │Pod 1│ │Pod 2│  │
  │   └─────┘ └─────┘ │    │   └─────┘ └─────┘  │
  └────────┬───────────┘    └────────┬───────────┘
           │                         │
  ─────────┘                         │
  Traffic ────────────────────────────┘  ← Switch DNS/Service
```

- Two identical environments (Blue = current, Green = new version).
- Deploy the new version to the Green environment; test it thoroughly.
- Switch the Service/DNS to point traffic from Blue → Green.
- If Green breaks, instantly switch back to Blue.
- **Best for:** High-stakes deployments where you need instant rollback (payment systems, compliance-heavy environments).
- **Tradeoff:** Requires double the infrastructure.

### Canary Deployment

```
  Traffic Distribution:

  ┌──────────────────────────────────────────────┐
  │  90% of traffic ──────────► Pods (v1)        │
  │  10% of traffic ──────────► Canary Pod (v2)  │
  └──────────────────────────────────────────────┘

  Phase 1: 10% → v2  (monitor for 10 min)
  Phase 2: 25% → v2  (monitor for 10 min)
  Phase 3: 50% → v2  (monitor for 10 min)
  Phase 4: 100% → v2 (full rollout)
```

- Route a small percentage of traffic (e.g., 10%) to the new version.
- Monitor error rates and latency for the canary pod.
- Gradually increase traffic if metrics are healthy.
- If the canary shows errors, instantly pull it and keep 100% on the stable version.
- **Best for:** ML model deployments where you want to validate real-world accuracy before full rollout.
- **Tradeoff:** Requires a service mesh (Istio, Linkerd) or advanced ingress configuration.

### Strategy Comparison

| Strategy | Downtime | Rollback Speed | Infrastructure Cost | Complexity |
|---|---|---|---|---|
| Rolling Update | Zero | ~60s (rollback previous ReplicaSet) | 1x | Low |
| Blue-Green | Zero | Instant (DNS/Service switch) | 2x | Medium |
| Canary | Zero | Instant (remove canary pod) | 1.1x | High |

---

## 3. Production Gate Patterns

In enterprise environments, the deploy step often includes multiple gates that must pass before code reaches production:

```
  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
  │   Lint   │──►│  Tests   │──►│  Build   │──►│  Gates   │──►│  Deploy  │
  └──────────┘   └──────────┘   └──────────┘   └────┬─────┘   └──────────┘
                                                     │
                                               ┌─────┴──────┐
                                               │ • Security │
                                               │   scan     │
                                               │ • License  │
                                               │   check    │
                                               │ • Manual   │
                                               │   approval │
                                               │ • AI Code  │
                                               │   Review   │
                                               └────────────┘
```

Gates include:
1. **Security Scanning**: Tools like Snyk, Semgrep, or your own **Jeevi AI Reviewer** scan for vulnerabilities.
2. **License Compliance**: Ensure no prohibited open-source licenses are present.
3. **Manual Approval**: A human reviewer approves the deployment (the `environment: production` gate you configured in Lesson 01).
4. **AI-Powered Review**: An LLM-based reviewer analyzes code quality and flags anti-patterns (like the Jeevi Guard pipeline from the `jeevisoft-platform`).

---

## Student Deliverables

To complete this module, submit the following deliverables to your instructor.

### Deliverable 1: CI/CD Pipeline Configuration
Submit your complete `.github/workflows/ci.yml` file showing the lint → test → build → deploy pipeline.

### Deliverable 2: Test Suite (5 Tests Passing)
Provide a screenshot or copy-paste of the `pytest tests/ -v` output showing all 5+ tests passing:
- 2 unit tests (chunking + embeddings)
- 2 integration tests (API health + DB query)
- 1 ML accuracy test (golden dataset)

### Deliverable 3: Autoscaler in Action
Provide screenshots showing:
- `kubectl get hpa --watch` output during a load test (showing replicas scaling from 2 → 3+).
- `kubectl get pods` output showing the additional pods that were created by HPA.

### Deliverable 4: Broken Pipeline Evidence
Provide screenshots showing:
- The GitHub Actions UI with the failed pipeline (red ❌ on the test step).
- The pipeline turning green after the fix is pushed.

### Deliverable 5: DORA Metrics Reflection (Written Answers)
Answer the following (2-3 sentences each):
1. **Scenario A**: Your team currently deploys once a week. Using the DORA framework, which metric is this, and what would you change to improve it to "Elite" level?
2. **Scenario B**: A canary deployment shows that 5% of requests to the new model version are returning HTTP 500 errors. What action should you take, and which DORA metric does this protect?
