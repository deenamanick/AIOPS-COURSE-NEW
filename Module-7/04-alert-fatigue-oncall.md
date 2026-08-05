# 04 — Alert Fatigue & On-Call Engineering

Alert fatigue occurs when responders receive too many low-value, duplicate, or unactionable notifications. The result is slower response and a higher chance of missing genuine user impact.

---

## Sources of Noise

- Alerts fire on every instance instead of the service symptom.
- `for` durations are too short.
- Alerts repeat too frequently.
- Downstream symptoms page alongside the root cause.
- Warnings and critical pages share the same route.
- Alerts lack ownership or a runbook.

Prefer multi-window SLO alerts for pages, capacity forecasts for slow resource exhaustion, and tickets for nonurgent maintenance.

---

## Lab: Create a 15-Alert Storm

The training app exposes a safe database-failure gauge. Activate it:

```bash
curl -X POST http://localhost:8080/drill/db-down
```

The lab rules create one `DatabaseDown` root-cause alert plus 14 downstream symptom alerts. After evaluation, inspect Prometheus and Alertmanager.

All alerts share `cluster="training"`. Alertmanager applies:

```yaml
inhibit_rules:
  - source_matchers: ['alertname="DatabaseDown"']
    target_matchers: ['dependency="database"']
    equal: [cluster]
```

The root cause remains visible while dependent app, web, queue, and worker notifications are inhibited. Grouping collects related alerts; inhibition removes redundant symptoms. These mechanisms solve different problems.

Reset the drill:

```bash
curl -X POST http://localhost:8080/drill/reset
```

Verify that resolved notifications arrive.

---

## On-Call Operating Model

An effective on-call system defines:

| Element | Example |
|---|---|
| Primary | Acknowledges within 5 minutes |
| Secondary | Engaged if primary does not acknowledge |
| Service owner | Provides application expertise |
| Incident commander | Coordinates severe multi-team incidents |
| Communications lead | Updates stakeholders and status page |

### Runbook Minimum

Every paging alert should link to a runbook containing:

1. Meaning and user impact.
2. Dashboard and verification queries.
3. Likely causes.
4. Safe diagnostic steps.
5. Mitigation and rollback.
6. Escalation criteria.
7. How to confirm recovery.

---

## Severity Guidance

| Severity | Meaning | Delivery |
|---|---|---|
| Critical | Active material user impact | Page immediately |
| Warning | Risk is developing; action soon | Chat/ticket during support hours |
| Info | Context or expected event | Dashboard/event stream |

Do not assign severity based only on which metric crossed a threshold. Base it on impact, urgency, and available response time.

---

## Debrief

- How many alerts fired in Prometheus?
- How many notifications reached the receiver?
- Which alerts were inhibited and why?
- Would `DatabaseDown` always be the root cause in production?
- What topology or ownership labels are needed for safe inhibition?
