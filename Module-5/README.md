# Module 5: Anomaly Detection with Machine Learning

Welcome to Module 5! In Module 4, you built CI/CD pipelines, automated tests, and configured autoscaling. Your application is now deployed, monitored, and scales automatically. But how do you detect **when something is going wrong** before users notice? Traditional monitoring relies on static thresholds ("alert when CPU > 90%"), but modern cloud-native systems exhibit complex, dynamic behavior that static rules cannot capture. In this module, you will train **machine learning models** to automatically detect anomalies in multi-dimensional telemetry data — without any labeled training data.

---

## Learning Objectives

By the end of this module, you will be able to:
1. Explain why **static thresholds fail** in dynamic, auto-scaling environments.
2. Train an **Isolation Forest** model on multi-dimensional telemetry (CPU, memory, network, disk).
3. Implement **Z-score** anomaly detection using standard deviations.
4. Implement **moving average** anomaly detection using rolling windows.
5. **Visualize anomalies** in telemetry data using Matplotlib.
6. **Compare** all three detection methods and understand when to use each.
7. Tune the **contamination parameter** to control false positive rates.

---

## Prerequisites

- ✅ Module 4 completed (CI/CD pipeline and Kubernetes cluster are operational)
- ✅ Python 3.11+ installed with `pip`
- ✅ Basic Python knowledge (variables, loops, if/else) — no data science experience needed
- ✅ No ML experience required — this module teaches everything from scratch

---

## Lab Architecture

In this module, you will build a complete anomaly detection pipeline that processes server telemetry:

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │                    ANOMALY DETECTION PIPELINE                        │
  │                                                                      │
  │   ┌──────────────┐   ┌──────────────────┐   ┌───────────────────┐   │
  │   │  Telemetry   │   │   Feature        │   │   ML Detection    │   │
  │   │  CSV Data    │──►│   Engineering    │──►│   Engine          │   │
  │   │              │   │                  │   │                   │   │
  │   │  • CPU %     │   │  • Normalization │   │  • Isolation      │   │
  │   │  • Memory %  │   │  • Windowing     │   │    Forest         │   │
  │   │  • Network   │   │  • Z-scores      │   │  • Z-Score        │   │
  │   │  • Disk %    │   │                  │   │  • Moving Average │   │
  │   └──────────────┘   └──────────────────┘   └────────┬──────────┘   │
  │                                                      │              │
  │                                                      ▼              │
  │                                        ┌──────────────────────────┐ │
  │                                        │    Visualization         │ │
  │                                        │    (Matplotlib)          │ │
  │                                        │                          │ │
  │                                        │  🔵 Normal   🔴 Anomaly  │ │
  │                                        └──────────────────────────┘ │
  └──────────────────────────────────────────────────────────────────────┘
```

---

## How to Set Up the Lab

### Step 1: Create a Virtual Environment

```bash
cd Module-5/lab
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

The `requirements.txt` includes: `numpy`, `pandas`, `scikit-learn`, `matplotlib`, and `jupyter` (optional, for interactive exploration).

---

## Lessons in this Module

| # | Lesson | What You'll Do |
|---|---|---|
| 01 | [Why Static Thresholds Fail](./01-static-thresholds-fail.md) | Understand the limitations of rule-based alerting in dynamic environments |
| 02 | [Isolation Forest](./02-isolation-forest.md) | Train an unsupervised ML model to detect anomalies in multi-dimensional telemetry |
| 03 | [Z-Score Detection](./03-zscore-detection.md) | Implement standard deviation-based anomaly detection and compare with Isolation Forest |
| 04 | [Moving Average Detection](./04-moving-average.md) | Implement rolling window smoothing and band-based anomaly flagging |
| 05 | [Break/Fix Activities](./05-break-fix.md) | Inject synthetic anomalies (CPU spikes, memory leaks, disk fills) and compare all 3 methods |
| 06 | [Bonus Lecture](./06-bonus-lecture.md) | Learn about production anomaly detection: streaming data, ensemble methods, and AIOps platforms |

Let's get started with **01-static-thresholds-fail.md**!
