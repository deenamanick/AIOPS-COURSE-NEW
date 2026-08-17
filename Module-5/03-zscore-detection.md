# 03 — Z-Score Anomaly Detection

In Lesson 02, we used an AI model (Isolation Forest) to detect anomalies. That's powerful, but it can feel like a "black box." In this lesson, we'll use a much simpler technique called **Z-Score** that you can understand with basic math — no AI required!

---

## Real-World Analogy: The Classroom Test

Imagine a class of 30 students takes a test. Most students score between 60 and 80. The class average is 70.

- A student who scores **71** is perfectly normal — right near the average.
- A student who scores **95** is unusual — way above everyone else.
- A student who scores **20** is also unusual — way below everyone else.

The Z-Score is simply a way to measure **"how far away from the average is this value?"** — expressed in units of standard deviation.

---

## What is a Z-Score?

The formula is simple:

```
Z-Score = (Value - Average) / Standard Deviation
```

### What does that mean in plain English?

| Term | Plain English | Example |
|---|---|---|
| **Value** | The number you're checking | CPU is at 95% |
| **Average (Mean)** | What CPU usually is | CPU is usually around 48% |
| **Standard Deviation** | How much CPU normally bounces around | CPU normally varies by about ±8% |
| **Z-Score** | How many "bounces" away from average | (95 - 48) / 8 = **5.9** — nearly 6 bounces away! |

### The Rule of Thumb

| Z-Score | What it means | Should we worry? |
|---|---|---|
| **0** | Exactly at the average | No — perfectly normal |
| **±1** | A little above/below average | No — 68% of data is here |
| **±2** | Noticeably above/below average | Maybe — only 5% of data is here |
| **±3 or more** | Extremely far from average | **Yes! Only 0.3% of data should be this far out** |

Think of it like a speed limit:
- Z-Score of 1 = driving 5 km/h over the limit (nobody cares)
- Z-Score of 2 = driving 20 km/h over (you might get noticed)
- Z-Score of 3+ = driving 60 km/h over (**definitely getting flagged!**)

```
  Normal Distribution (Bell Curve):

  How many
  data points
     │
     │          ┌────┐
     │       ┌──┤    ├──┐
     │    ┌──┤  │    │  ├──┐
     │ ┌──┤  │  │    │  │  ├──┐
     │─┤  │  │  │    │  │  │  ├─
     └──┴──┴──┴──┴────┴──┴──┴──┴──
      -3   -2  -1  avg  +1  +2  +3
       │                        │
       └── ANOMALY ZONE ────────┘
           (less than 0.3% of data)
```

---

## Lab: Let's Detect Anomalies with Z-Scores

### Step 1: Calculate Z-Scores for Each Server Metric

```python
import pandas as pd    # pandas = a library for working with spreadsheets in Python
import numpy as np     # numpy  = a library for doing math on lists of numbers

# ───────────────────────────────────────────────────────
# STEP 1: Load our server data into a "spreadsheet" (DataFrame)
# ───────────────────────────────────────────────────────
df = pd.read_csv('server_telemetry.csv')

# These are the 4 server metrics we want to check for anomalies
features = ['cpu_percent', 'memory_percent', 'network_mbps', 'disk_iops']

# ───────────────────────────────────────────────────────
# STEP 2: Set our Z-Score threshold
# ───────────────────────────────────────────────────────
# We'll flag anything with a Z-Score above 3 (or below -3).
# This means: "flag data points that are 3+ standard deviations away from normal."
z_threshold = 3

# ───────────────────────────────────────────────────────
# STEP 3: Calculate Z-Score for each metric column
# ───────────────────────────────────────────────────────
for col in features:
    # Calculate the average value for this column
    average = df[col].mean()      # e.g., average CPU is 48%

    # Calculate the standard deviation (how much the values normally bounce around)
    std_dev = df[col].std()       # e.g., CPU normally varies by about 8%

    # Apply the Z-Score formula to every row: (Value - Average) / Std Dev
    df[f'{col}_zscore'] = (df[col] - average) / std_dev

    # Print what we calculated so the student can see it
    print(f"  {col}: average = {average:.1f}, std dev = {std_dev:.1f}")

# ───────────────────────────────────────────────────────
# STEP 4: Flag rows as "anomaly" or "normal"
# ───────────────────────────────────────────────────────
# A row is an anomaly if ANY of its 4 metrics has a Z-Score beyond our threshold.
# For example, if CPU Z-Score is 4.5, that row is flagged even if memory is normal.

zscore_cols = [f'{col}_zscore' for col in features]

# This line checks every row: "Does ANY column have |Z-Score| > 3?"
#   -1 means "Anomaly"
#    1 means "Normal"
df['zscore_anomaly'] = df[zscore_cols].apply(
    lambda row: -1 if any(abs(row) > z_threshold) else 1,
    axis=1   # axis=1 means "check each row" (not each column)
)

# Count how many rows were flagged
n_anomalies = (df['zscore_anomaly'] == -1).sum()
n_normal = (df['zscore_anomaly'] == 1).sum()
print(f"\n🔴 Anomalies detected: {n_anomalies}")
print(f"🔵 Normal data points: {n_normal}")
```

Expected Output:
```text
  cpu_percent: average = 48.5, std dev = 8.7
  memory_percent: average = 63.2, std dev = 10.2
  network_mbps: average = 492.3, std dev = 45.8
  disk_iops: average = 208.4, std dev = 32.2

🔴 Anomalies detected: 32
🔵 Normal data points: 968
```

### Step 2: Visualize the Results

```python
import matplotlib.pyplot as plt

# Split our data into two groups
normal = df[df['zscore_anomaly'] == 1]       # rows where zscore_anomaly == 1
anomalies = df[df['zscore_anomaly'] == -1]   # rows where zscore_anomaly == -1

# Create a 2x2 grid of charts
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Z-Score Anomaly Detection (Threshold: 3σ)', fontsize=16, fontweight='bold')

# We'll plot 4 different pairs of metrics to see where anomalies appear
plot_pairs = [
    ('cpu_percent', 'memory_percent', 'CPU vs Memory'),
    ('cpu_percent', 'network_mbps', 'CPU vs Network'),
    ('memory_percent', 'disk_iops', 'Memory vs Disk I/O'),
    ('network_mbps', 'disk_iops', 'Network vs Disk I/O'),
]

for ax, (x_col, y_col, title) in zip(axes.flat, plot_pairs):
    # Plot normal data as small blue dots
    ax.scatter(normal[x_col], normal[y_col], c='steelblue', s=10, alpha=0.5, label='Normal')
    # Plot anomalies as big red X marks
    ax.scatter(anomalies[x_col], anomalies[y_col], c='red', s=40, marker='x', label='Anomaly')
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title)
    ax.legend(loc='upper right', fontsize=8)

plt.tight_layout()
plt.savefig('zscore_results.png', dpi=150)
plt.show()
print("📊 Plot saved to zscore_results.png")
```

### Step 3: Which Metrics Contributed Most?

Let's see which server metric triggered the most anomaly flags:

```python
print("Per-metric breakdown:")
print("=" * 50)
for col in features:
    z_col = f'{col}_zscore'
    # Find rows where this specific metric's Z-Score exceeded our threshold
    flagged = df[df[z_col].abs() > z_threshold]
    # Find the single highest Z-Score in this metric
    max_z = df[z_col].abs().max()
    print(f"  {col}: {len(flagged)} rows flagged (worst Z-Score: {max_z:.2f})")
```

Expected Output:
```text
Per-metric breakdown:
==================================================
  cpu_percent: 18 rows flagged (worst Z-Score: 5.81)
  memory_percent: 12 rows flagged (worst Z-Score: 3.42)
  network_mbps: 8 rows flagged (worst Z-Score: 4.15)
  disk_iops: 15 rows flagged (worst Z-Score: 6.27)
```

**Reading the output:** Disk I/O had the highest Z-Score (6.27), meaning some disk values were over 6 standard deviations away from normal — extremely unusual!

---

## When Z-Scores Work Well (and When They Don't)

### ✅ Z-Scores are great when:
- You want a **simple, fast** anomaly check with no AI/ML setup.
- Your data roughly follows a bell curve (most server metrics do).
- You need **real-time** detection — Z-Score is just one subtraction and one division.

### ❌ Z-Scores struggle when:

| Problem | Example |
|---|---|
| **Gradual changes** | A memory leak that climbs 0.5% per hour. Each individual reading has a "normal" Z-Score, but the trend is clearly broken. |
| **Multi-dimensional patterns** | CPU at 80% alone might be fine. Memory at 85% alone might be fine. But both at the same time could mean trouble. Z-Score checks each metric independently. |
| **Data that isn't bell-shaped** | Disk I/O bursts can be "spiky" — many zeros with occasional huge jumps. Z-Scores assume smooth bell curves. |

This is why Isolation Forest (Lesson 02) often outperforms Z-Scores — it looks at all metrics together in multi-dimensional space.

---

## What's Next

Z-Scores compare each data point against the **entire dataset's average**. But what if "normal" changes over time? (A server at 3 AM behaves differently than at 3 PM.) In the next lesson, we'll use **Moving Average** detection, which compares each data point against its **recent neighbors** instead.
