# 01 — Actionable Alerting & Alertmanager

An alert is useful only when it identifies user impact, reaches the correct owner, and suggests an action. A dashboard is for exploration; a page interrupts a person and therefore requires a higher standard.

---

## Alert Pipeline

```text
PromQL expression → pending → firing → Alertmanager → grouped notification
                                             ├── route by team/severity
                                             ├── inhibit dependent symptoms
                                             └── silence planned work
```

Prometheus evaluates the condition. Alertmanager does not evaluate PromQL; it receives firing and resolved alerts, groups them, suppresses redundant notifications, and routes the result.

### Alert States

| State | Meaning |
|---|---|
| Inactive | Expression is false |
| Pending | Expression is true, but the `for` duration has not elapsed |
| Firing | Expression remained true for the required duration |
| Resolved | A previously firing condition is false |

The `for` clause prevents one noisy sample from paging someone.

---

## Symptom-Based vs Cause-Based Alerting

Page on symptoms that users experience:

- sustained 5xx ratio;
- availability below the SLO;
- p99 latency above the service objective.

Use cause signals such as high CPU, disk pressure, or database connections for diagnosis or lower-severity tickets. A CPU alert without user impact may not require an immediate page.

| Signal | Typical action |
|---|---|
| User-visible error-rate breach | Page service owner |
| Imminent disk exhaustion | Page infrastructure owner |
| Brief CPU spike | Dashboard only |
| Exporter missing for 15 minutes | Ticket or monitoring alert |

---

## Alertmanager Configuration

The lab's `alertmanager/alertmanager.yml` demonstrates:

```yaml
route:
  receiver: default-notifications
  group_by: [cluster, alertname]
  group_wait: 15s
  group_interval: 1m
  repeat_interval: 4h
```

- `group_wait`: wait briefly for related alerts before sending the first message.
- `group_interval`: minimum delay before sending changes to an existing group.
- `repeat_interval`: how long before repeating an unchanged notification.
- `group_by`: labels that define which alerts share a notification.

### Silence vs Inhibition

A **silence** is a time-bounded manual matcher, useful during planned maintenance. **Inhibition** is an automatic dependency rule: if the database is down, suppress downstream app alerts that share the same cluster.

Never use a silence to hide an unexplained incident. Record an owner, reason, and expiry.

---

## Lab: Inspect the Notification Path

```bash
cd Module-7/lab
docker compose up -d --build
curl -s http://localhost:8080/health
```

1. Open Prometheus **Status → Runtime & Build Information** and verify Alertmanager discovery.
2. Open Alertmanager and inspect routes and active alerts.
3. Open Mailpit at `http://localhost:8025`.
4. Open the webhook receiver at `http://localhost:5001/alerts`.

The local receivers let you study notification payloads safely. Production secrets belong in a secret manager, not committed YAML.

---

## Alert Quality Checklist

Every paging alert should answer:

- What user-visible condition is failing?
- Which service and environment are affected?
- How severe is it?
- Who owns it?
- What dashboard and runbook should the responder open?
- When does it escalate?

In the next lesson, you will implement and validate three Prometheus alert rules.
