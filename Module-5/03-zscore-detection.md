# 03 — Z-Score Anomaly Detection

While Isolation Forest uses an ensemble of random trees, Z-score anomaly detection uses a much simpler approach rooted in basic statistics. A **Z-score** measures how many standard deviations a data point is away from the mean. If a data point is far enough from the center of the distribution, it's likely an anomaly.

---

## What is a Z-Score?

The Z-score of a value `x` is calculated as:

```
Z = (x - μ) / σ

Where:
  x = the observed value
  μ = the mean of the dataset
  σ = the standard deviation of the dataset
```

### Interpreting Z-Scores

| Z-Score | Meaning | Probability (Normal Distribution) |
|---|---|---|
| 0 | Exactly at the mean | 50% of data is above/below |
| ±1 | 1 standard deviation from mean | ~68% of data falls within |
| ±2 | 2 standard deviations from mean | ~95% of data falls within |
| ±3 | 3 standard deviations from mean | ~99.7% of data falls within |
| > ±3 | **Anomaly zone** | Only ~0.3% of data should be here |

```
  Normal Distribution with Z-Score Boundaries:

  Count
    │
    │          ┌────┐
    │       ┌──┤    ├──┐
    │    ┌──┤  │    │  ├──┐
    │ ┌──┤  │  │    │  │  ├──┐
    │─┤  │  │  │    │  │  │  ├─
    └──┴──┴──┴──┴────┴──┴──┴──┴──
     -3σ -2σ -1σ  μ  +1σ +2σ +3σ
      │                        │
      └── ANOMALY ZONE ────────┘
```

---

## Lab: Implementing Z-Score Detection

### Step 1: Calculate Z-Scores for All Metrics

```python
import pandas as pd
import numpy as np

# Load data into our spreadsheet
df = pd.read_csv('server_telemetry.csv')
features = ['cpu_percent', 'memory_percent', 'network_mbps', 'disk_iops']

# Calculate Z-scores for each feature
z_threshold = 3  # Flag anything beyond 3 standard deviations (very rare events)

for col in features:
    # .mean() calculates the average, .std() calculates the standard deviation
    mean = df[col].mean()
    std = df[col].std()
    # The Z-score formula: (Value - Mean) / Standard Deviation
    df[f'{col}_zscore'] = (df[col] - mean) / std

# Flag a row as anomalous (-1) if ANY feature has an absolute Z-score > 3
zscore_cols = [f'{col}_zscore' for col in features]
# .apply() runs a custom check on every single row
df['zscore_anomaly'] = df[zscore_cols].apply(
    lambda row: -1 if any(abs(row) > z_threshold) else 1, axis=1
)

n_anomalies = (df['zscore_anomaly'] == -1).sum()
print(f"🔴 Z-Score anomalies detected (threshold={z_threshold}σ): {n_anomalies}")
```

Expected Output:
```text
🔴 Z-Score anomalies detected (threshold=3σ): 32
```

### Step 2: Visualize Z-Score Results

```python
import matplotlib.pyplot as plt

normal = df[df['zscore_anomaly'] == 1]
anomalies = df[df['zscore_anomaly'] == -1]

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Z-Score Anomaly Detection (Threshold: 3σ)', fontsize=16, fontweight='bold')

plot_pairs = [
    ('cpu_percent', 'memory_percent', 'CPU vs Memory'),
    ('cpu_percent', 'network_mbps', 'CPU vs Network'),
    ('memory_percent', 'disk_iops', 'Memory vs Disk I/O'),
    ('network_mbps', 'disk_iops', 'Network vs Disk I/O'),
]

for ax, (x_col, y_col, title) in zip(axes.flat, plot_pairs):
    ax.scatter(normal[x_col], normal[y_col], c='steelblue', s=10, alpha=0.5, label='Normal')
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

### Step 3: Per-Feature Z-Score Breakdown

Which metrics contributed most to the anomaly flags?

```python
for col in features:
    z_col = f'{col}_zscore'
    # df[z_col].abs() gets the absolute value (ignoring negative signs)
    flagged = df[df[z_col].abs() > z_threshold]
    # df[z_col].abs().max() finds the single highest Z-score in the column
    print(f"  {col}: {len(flagged)} data points flagged (max |Z|: {df[z_col].abs().max():.2f})")
```

Expected Output:
```text
  cpu_percent: 18 data points flagged (max |Z|: 5.81)
  memory_percent: 12 data points flagged (max |Z|: 3.42)
  network_mbps: 8 data points flagged (max |Z|: 4.15)
  disk_iops: 15 data points flagged (max |Z|: 6.27)
```

---

## Z-Score Limitations

| Limitation | Description |
|---|---|
| **Assumes Normal Distribution** | Z-scores assume data follows a bell curve. Skewed distributions (like disk I/O bursts) will produce inaccurate scores. |
| **Single-Dimensional** | Each metric is evaluated independently. A point where CPU=85% AND memory=90% AND disk=1500 might be individually "normal" on each axis but is clearly anomalous when considered together. |
| **Sensitive to Outliers** | The mean and standard deviation are themselves skewed by the outliers you're trying to detect, creating a circular problem. |

This is precisely why Isolation Forest (Lesson 02) often outperforms Z-scores — it evaluates data points in multi-dimensional space and doesn't assume any particular distribution.

---

## What's Next

Z-scores analyze each data point in isolation (no concept of time). In the next lesson, we will implement **moving average** detection, which uses a sliding time window to detect anomalies relative to recent trends rather than the global mean.
