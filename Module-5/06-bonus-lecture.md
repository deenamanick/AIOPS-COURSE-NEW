# 06 — Production Anomaly Detection & Deliverables

Congratulations on completing the core lab components of Module 5! You've trained models, compared algorithms, and benchmarked their accuracy. Before you submit your deliverables, let's explore how enterprise SRE teams scale anomaly detection to production.

---

## 1. Streaming Anomaly Detection

In the lab, you processed a static CSV file. In production, telemetry arrives as a **continuous stream** — thousands of metrics per second from hundreds of servers. You cannot retrain a model on every new data point.

### Online Learning Approaches

| Approach | How It Works | Latency |
|---|---|---|
| **Sliding Window Retrain** | Retrain the Isolation Forest every N minutes on the last 1 hour of data. | Minutes |
| **Incremental Learning** | Use algorithms like Half-Space Trees that update with each new data point. | Milliseconds |
| **Pre-trained + Inference** | Train the model offline on historical data, deploy it as a microservice, and send each new data point for scoring. | Milliseconds |

```
  Production Streaming Pipeline:

  Prometheus/    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  Datadog   ────►│  Kafka /     │───►│  Anomaly     │───►│  PagerDuty / │
  (metrics)      │  Kinesis     │    │  Detection   │    │  Slack Alert │
                 │  (stream)    │    │  (ML Model)  │    │  (response)  │
                 └──────────────┘    └──────────────┘    └──────────────┘
```

---

## 2. Ensemble Methods

No single algorithm catches every anomaly type. Production systems combine multiple detectors:

```
  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
  │ Isolation Forest │   │    Z-Score      │   │ Moving Average  │
  │   (score: 0.82)  │   │  (score: 0.91)  │   │  (score: 0.75)  │
  └────────┬─────────┘   └────────┬────────┘   └────────┬────────┘
           │                      │                     │
           └──────────────────────┼─────────────────────┘
                                  ▼
                        ┌──────────────────┐
                        │  Ensemble Voter  │
                        │                  │
                        │  If 2/3 models   │
                        │  agree → ANOMALY │
                        └────────┬─────────┘
                                 ▼
                        ┌──────────────────┐
                        │   Alert / Action │
                        └──────────────────┘
```

### Voting Strategies

| Strategy | Rule | Tradeoff |
|---|---|---|
| **Majority Vote** | Flag if ≥2 out of 3 detectors agree | Balanced: reduces false positives without missing too many anomalies |
| **Any Vote** | Flag if any 1 detector fires | Aggressive: catches everything but produces more false alarms |
| **Weighted Vote** | Each detector has a confidence weight | Optimal: requires calibration but produces the best results |

---

## 3. Automated Incident Response (AIOps)

The most advanced AIOps platforms don't just detect anomalies — they **automatically respond** to them:

| Response Level | Example | Automation |
|---|---|---|
| **Level 1: Alert** | Send a Slack/PagerDuty notification. | Fully automated |
| **Level 2: Diagnose** | Correlate the anomaly with recent deployments, config changes, or known incidents. | Semi-automated (LLM-assisted) |
| **Level 3: Remediate** | Trigger a runbook: restart the service, scale up pods, or roll back the deployment. | Requires human approval (for now) |
| **Level 4: Self-Heal** | Automatically execute remediation without human intervention. | Fully automated (requires high confidence) |

This is the vision behind the **AIOps assistant** you built in Modules 1-4. By combining anomaly detection (Module 5) with LLM-powered root cause analysis (Module 1) and automated CI/CD (Module 4), you create a system that can detect, diagnose, and potentially fix production issues autonomously.

---

## 4. Feature Engineering for Better Detection

The raw metrics (CPU, memory, network, disk) can be enhanced with derived features:

| Derived Feature | Formula | Why It Helps |
|---|---|---|
| **Rate of Change** | `delta_cpu = cpu[t] - cpu[t-1]` | Detects sudden changes, even if the absolute value is "normal" |
| **Rolling Variance** | `var(cpu, window=10)` | Detects instability — a metric that's swinging wildly is suspicious |
| **Cross-Metric Ratio** | `cpu / memory` | Detects unusual resource proportions (e.g., CPU spiking while memory drops) |
| **Time-of-Day Encoding** | `sin(2π × hour/24)` | Allows the model to learn diurnal patterns |

Adding these features to your Isolation Forest model typically improves detection accuracy by 10-20%.

---

## Student Deliverables

To complete this module, submit the following deliverables to your instructor.

### Deliverable 1: Isolation Forest Results
Submit:
- Your `isolation_forest_results.png` plot (2x2 grid showing normal vs anomaly in blue/red).
- The printed output showing the number of anomalies detected and the top 10 most anomalous data points.

### Deliverable 2: Z-Score & Moving Average Results
Submit:
- Your `zscore_results.png` plot.
- Your `moving_average_results.png` plot (4 time-series with rolling bands).

### Deliverable 3: Comparison Report
Submit the output of `compare_detectors.py` showing:
- Detection rates for each anomaly type (CPU spike, memory leak, disk fill).
- False positive counts for each method.

### Deliverable 4: Contamination Experiment
Run Isolation Forest with `contamination` values of 0.01, 0.05, and 0.10. Submit the output showing how the number of detected anomalies changes.

### Deliverable 5: SRE Reflections (Written Answers)
Answer the following (2-3 sentences each):
1. **Scenario A**: Your monitoring team is overwhelmed with false alerts. You currently use Z-score with a threshold of 2σ. What two changes would you recommend to reduce false positives while still catching real anomalies?
2. **Scenario B**: A production memory leak causes a gradual increase of 0.5% per hour over 12 hours. Which of the three methods would detect this earliest, and why? What window size would you recommend for the moving average approach?
