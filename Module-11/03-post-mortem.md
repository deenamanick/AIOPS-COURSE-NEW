# 03 — Blameless Post-Mortems

A post-mortem (also called an incident review or learning review) is a structured document written after an outage that answers: what happened, why did it happen, what was the impact, and what will we change so it never happens again?

The word **blameless** is the most important word in that sentence. A blame-focused post-mortem identifies the person who made the mistake and punishes or shames them. A blameless post-mortem identifies the **system** that made the mistake possible and fixes the system. The engineer who makes the same mistake twice may simply be working in a system designed to produce that mistake.

---

## Why Blameless?

Three reasons:

1. **Blame hides information.** Engineers who fear punishment underreport near-misses, hide contributing factors, and give vague root causes. You get a worse post-mortem.
2. **Blame doesn't fix systems.** Firing the engineer who made a mistake doesn't change the broken process, missing check, or absent alert that allowed the mistake to cause an outage.
3. **Blame erodes psychological safety.** Teams with low psychological safety take fewer risks, ship more slowly, and hide problems — all of which makes reliability *worse* over time.

Google's SRE book states: _"We want to enable the rapid discovery of the root cause of an outage without fear of punishment."_ Netflix, Spotify, and Etsy all operate the same way.

---

## The Industry-Standard Post-Mortem Template

The template used at Google, Atlassian, and PagerDuty:

```markdown
# Post-Mortem: [Incident Title]
**Date**: YYYY-MM-DD
**Authors**: [Your name(s)]
**Severity**: SEV-1 / SEV-2 / SEV-3
**Status**: In Review / Approved

---

## Impact Summary
- **Duration**: HH:MM (from first symptom to full recovery)
- **User impact**: [What users experienced]
- **Services affected**: [List of services]
- **Revenue/SLO impact**: [If measurable]

---

## Timeline
| Time (UTC) | Event |
|---|---|
| 06:43:40 | First log error: WAL archive rotation failed |
| 06:44:10 | Alertmanager fires DiskAlmostFull |
| 06:45:00 | On-call paged |
| 06:52:00 | Root cause identified (WAL archive disk full) |
| 06:55:00 | Ansible playbook clear-logs.yml executed |
| 07:01:00 | Disk below 80%, DB writes resuming |
| 07:08:00 | Error rate back to baseline. All-clear declared. |

---

## Root Cause
[Single root cause — the deepest cause in the chain]

---

## Contributing Factors
[Secondary factors that worsened or enabled the incident]
[Use "5 Whys" to get to the real root cause, not the surface symptom]

---

## What Went Well
[Honest list of things the team did right — detection speed, communication, etc.]

---

## What Went Wrong
[Honest list of failures — slow detection, wrong first action, missing alert, etc.]
[Frame as system failures, not individual failures]

---

## Where We Got Lucky
[Near-misses — things that could have been much worse]

---

## Action Items
| Action | Owner | Due Date | Priority |
|---|---|---|---|
| Configure WAL archive retention | DB team | 2026-08-18 | P1 |
| Add predictive disk alert for WAL dir | SRE team | 2026-08-15 | P1 |
| Reduce DB connection timeout to 5s | App team | 2026-08-20 | P2 |
| Run game day for DB disk-full scenario | SRE team | 2026-09-01 | P2 |

---

## Lessons Learned
[2–3 sentences summarising the systemic insight from this incident]
```

---

## The 5 Whys Technique

Post-mortems often stop at the surface symptom. The **5 Whys** technique drills down to the real root cause:

```text
Symptom: The application returned 503 errors.

Why 1: Because the database rejected all write connections.
Why 2: Because PostgreSQL could not write WAL entries.
Why 3: Because the disk was full.
Why 4: Because WAL archive files accumulated without being deleted.
Why 5: Because the log rotation job was configured for /var/log/app
       but not for /var/lib/postgresql/wal_archive.

Root Cause: Log rotation policy did not cover the WAL archive directory.
```

The 5 Whys reveals that the root cause is a **configuration gap in the log rotation policy** — not "the disk was full" (symptom) and not "the engineer forgot to configure log rotation" (blame).

The fix: add `/var/lib/postgresql/wal_archive` to the logrotate configuration. That is specific, actionable, and systemic.

---

## Lab: Write a Post-Mortem

The lab provides a simulated incident report as input. Write the post-mortem using the template.

### Use the Template

```bash
cp lab/templates/post-mortem-template.md lab/output/post-mortem-$(date +%Y%m%d).md
```

Open the file and fill in each section based on the capstone incident. The LLM RCA from Lesson 02 provides most of the raw content — your job is to reframe it into the blameless post-mortem structure.

### Section-by-Section Guidance

**Impact Summary**
Calculate duration from the earliest log error to the all-clear timestamp. Be specific about user impact: "all write operations to /api/checkout failed" is better than "the app was slow."

**Timeline**
Copy the LLM-generated timeline, add timestamps for team actions (who paged whom, first response action, fix applied, verified). Include the `[INJECT]` time if this was a drill.

**Root Cause**
Use the deepest Why from your 5 Whys analysis. One sentence, maximum. If you need multiple sentences, you are describing contributing factors, not the root cause.

**What Went Well**
This section is often skipped. Don't skip it. It is the most important section for team morale. If the alert fired in 8 seconds — write that. If the on-call responded in 3 minutes — write that. If the Ansible playbook fixed it automatically — write that.

**Action Items**
Every action item must have: what will change, who owns it, and a due date. Action items without owners and due dates are wishes, not commitments. Aim for 3–6 items. Fewer is fine if they are high impact.

---

## Common Post-Mortem Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| "Human error" as root cause | Hides systemic failure | Ask: what made this human error possible? |
| No "What Went Well" section | Demoralises team | Always credit what worked |
| Action items with no owner | Nothing gets done | Assign a name, not a team |
| Action items with no due date | Nothing gets done | Set a specific date |
| Written 2 weeks after the incident | Details are forgotten | Write within 24 hours |
| Longer than 3 pages | Nobody reads it | Be concise; details go in appendix |
| Blame embedded in "factual" timeline | Destroys psychological safety | Review draft with team before publishing |

---

## Post-Mortem Review Process

1. **Draft within 24 hours** — memories fade fast; the on-call writes the first draft.
2. **Peer review within 48 hours** — at least one other engineer reads for accuracy and blamelessness.
3. **Team review at weekly incident review** — 15-minute discussion of lessons and action items.
4. **Action item tracking** — review action item completion at the following week's meeting.
5. **Archive publicly** — post-mortems shared across the organisation build a shared learning library.

---

## Validation Checklist

- [ ] Post-mortem written using the template with all sections present.
- [ ] 5 Whys completed; root cause is a system failure, not a human failure.
- [ ] Timeline includes times for: first symptom, first alert, first response, fix applied, all-clear.
- [ ] "What Went Well" section has at least two genuine positive observations.
- [ ] All action items have an owner and a due date.
- [ ] No instance of "human error" used as a root cause without a deeper Why.
- [ ] Document is under 3 pages (excluding timeline and action items table).
