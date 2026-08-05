# 06 — Production SRE Patterns & Deliverables

Threshold alerts are useful for learning, but mature SRE teams page on how quickly an SLO is being consumed. This connects urgency directly to user impact.

---

## Burn Rate

Burn rate compares the observed bad-event rate with the allowed rate.

```text
burn rate = observed error rate / allowed error rate
```

For a 99.5% SLO, the allowed error rate is 0.5%. An observed 5% error rate burns budget at `5 / 0.5 = 10×`. If sustained, a 30-day budget would be exhausted in about three days.

### Multi-Window Alerting

Use a short window to detect fast failures and a long window to confirm persistence. Common policy shapes include:

- very high burn over minutes: page immediately;
- moderate burn over hours: page during support hours;
- slow burn over days: create a ticket.

Multi-window alerts reduce noise while protecting both acute and gradual reliability loss.

---

## Governance and Review

Treat alerts as production code:

- version-control and peer-review rules;
- unit-test PromQL expressions;
- validate Prometheus and Alertmanager configuration in CI;
- assign an owner and runbook;
- review noisy, unused, and unactionable alerts after incidents;
- track time to detect, acknowledge, mitigate, and resolve;
- test routing regularly with controlled drills.

---

## Student Deliverables

### Deliverable 1: Alert Rules

Submit the `HighCPU`, `HighErrorRate`, and `DiskAlmostFull` rules plus successful `promtool` output.

### Deliverable 2: Notification Evidence

Submit screenshots of:

- one alert in pending and firing states;
- the Alertmanager group;
- the local email or webhook notification;
- the resolved notification.

### Deliverable 3: SLO Document

Define the Flask service's availability and latency SLIs, 99.5% 30-day SLO, exclusions, data source, ownership, and error-budget policy. Show the calculation proving a 216-minute monthly budget.

### Deliverable 4: Alert-Fatigue Report

Document:

- the 15 alerts produced by the database drill;
- grouping labels;
- inhibition source, targets, and equality labels;
- the final actionable notification count;
- risks of incorrect inhibition.

### Deliverable 5: Error-Budget Incident Report

Include a timeline, SLI graph, remaining-budget graph, policy decision, remediation, recovery evidence, and one prevention action.

---

## Module Summary

You can now convert telemetry into actionable alerts, route notifications, suppress dependent symptoms, define service reliability mathematically, and use an error budget to balance feature delivery with reliability work. In Module 8, you will enrich logs and correlate multiple signals into one incident and root cause.
