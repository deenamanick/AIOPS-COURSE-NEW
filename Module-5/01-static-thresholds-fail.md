# 01 — Why Static Thresholds Fail

Before diving into machine learning, you need to understand **why** traditional monitoring breaks down in modern cloud environments. If static thresholds worked perfectly, we wouldn't need ML-based anomaly detection at all.

---

## What Are Static Thresholds?

A static threshold is a hard-coded rule: "Alert me when metric X crosses value Y."

Examples:
- Alert when CPU > 90%
- Alert when memory > 85%
- Alert when response latency > 500ms
- Alert when disk usage > 80%

These rules are simple, understandable, and have been the backbone of monitoring for decades.

---

## Why They Fail in Dynamic Environments

### Problem 1: Auto-Scaling Invalidates Fixed Baselines

In Module 4, you configured HPA to scale pods from 2 to 5 based on CPU utilization. Consider this scenario:

```
  Normal State (2 pods):  CPU per pod = 60%  ← Under threshold, no alert
  After scale-up (5 pods): CPU per pod = 25% ← Under threshold, no alert
  After scale-down (2 pods): CPU per pod = 75% ← Under threshold, no alert
```

The "normal" CPU level shifts constantly depending on the pod count. A static threshold of 90% will never fire because HPA intervenes first. But what if HPA fails to scale? The CPU will spike to 99% on both pods, and by the time the alert fires, users are already experiencing timeouts.

**The real question isn't "is CPU above 90%?" — it's "is CPU behaving differently than expected given the current pod count?"**

### Problem 2: Diurnal Patterns (Day/Night Cycles)

Most applications experience predictable traffic patterns:

```
  Traffic Pattern (24 hours):

  CPU %
  100 │
   80 │              ┌────┐
   60 │         ┌────┘    └────┐
   40 │    ┌────┘              └────┐
   20 │────┘                        └────
    0 └──────────────────────────────────
      00:00  06:00  12:00  18:00  00:00
              Peak hours: 10am - 6pm
```

- A threshold of **CPU > 80%** will fire every day during peak hours — creating **alert fatigue**.
- A threshold of **CPU > 95%** will miss real anomalies during off-peak hours, where 60% CPU at 3 AM is actually abnormal.

**Static thresholds cannot distinguish "normal-for-this-time-of-day" from "genuinely anomalous."**

### Problem 3: Multi-Dimensional Correlation

A CPU spike alone might not be an anomaly. But a CPU spike **combined** with a memory increase **and** a network drop **and** a disk I/O surge — that pattern almost certainly indicates a real incident.

```
  Metric        Normal    Anomaly
  ─────────────────────────────────
  CPU           45%       92%    ← Individually: could be normal during peak
  Memory        60%       88%    ← Individually: could be a cache warm-up
  Network In    500 Mbps  50 Mbps ← Individually: could be low traffic
  Disk I/O      200 IOPS  1800 IOPS ← Individually: could be a backup job

  Together? → Almost certainly a runaway process or attack.
```

Static thresholds evaluate each metric **independently**. They cannot detect correlated multi-dimensional anomalies.

---

## The Solution: Unsupervised Machine Learning

Instead of manually defining rules, we let a machine learning model **learn** what "normal" looks like by observing historical data. Any data point that deviates significantly from the learned normal behavior is flagged as an anomaly.

| Approach | How It Works | Strengths | Weaknesses |
|---|---|---|---|
| **Static Thresholds** | Fixed rules: "if X > Y, alert" | Simple, interpretable, fast | Can't handle dynamics, diurnal patterns, or correlations |
| **Z-Score** | Flags data points > N standard deviations from the mean | Simple statistics, no training needed | Assumes normal distribution, single-dimensional |
| **Moving Average** | Compares current value to a rolling mean | Smooths noise, detects trends | Lags behind sudden changes, single-dimensional |
| **Isolation Forest** | ML model that isolates outliers using random decision trees | Multi-dimensional, adapts to data shape, no labels needed | Requires tuning, less interpretable |

---

## Key Terminology

| Term | Definition |
|---|---|
| **Anomaly** | A data point that deviates significantly from expected behavior. Also called an "outlier." |
| **Unsupervised Learning** | ML that learns patterns from unlabeled data (no human tells it what's "normal" vs "anomalous"). |
| **Contamination** | The expected proportion of anomalies in the dataset (e.g., 0.05 = 5%). Used to tune sensitivity. |
| **False Positive** | A normal data point incorrectly flagged as anomalous. Too many = alert fatigue. |
| **False Negative** | An anomalous data point that was missed. Too many = undetected incidents. |
| **Telemetry** | Metrics collected from running systems: CPU, memory, disk, network, latency, error rates. |

---

## What's Next

Now that you understand why static thresholds aren't enough, let's train our first ML model. In the next lesson, you will load a real telemetry dataset, train an **Isolation Forest** model, and visualize the anomalies it detects.
