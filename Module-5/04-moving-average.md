# 04 — Moving Average Anomaly Detection

In Lesson 03, we used Z-Scores to flag data points that are far from the **overall average** of the entire dataset. But here's the problem: what if "normal" changes over time?

---

## Real-World Analogy: Your Body Temperature

Your body temperature is normally around 36.6°C. But it's not exactly 36.6 every single minute:
- At 6 AM when you wake up, it might be **36.2°C** (a bit cool — normal for morning).
- At 3 PM after lunch and work, it might be **37.0°C** (a bit warm — normal for afternoon).
- At 3 AM while sleeping, it might be **36.0°C** (cool — normal for deep sleep).

Now, if your temperature hits **37.5°C** at 3 PM, is that an anomaly? Compared to the morning, yes! But compared to the afternoon average, it's just slightly elevated. **Context matters.**

A **Moving Average** solves this problem by asking: *"How does this value compare to the RECENT past?"* — not the entire history.

---

## What is a Moving Average?

Instead of calculating ONE average for the entire dataset, we calculate a **sliding average** that moves along with the data.

```
  Example: Moving Average with a window of 3

  Raw Data:    10,  12,  11,  50,  13,  12
                └───┬───┘
                avg = 11     ← Average of first 3 values

  Raw Data:    10,  12,  11,  50,  13,  12
                     └───┬───┘
                     avg = 24.3  ← Average of next 3 values
                                    (includes the spike of 50!)

  The "50" stands out because it's far from its neighbors (11, 12).
```

### The "Band" Concept

We don't just calculate the moving average — we also calculate a **band** (safe zone) around it:

```
  The Safe Zone:

  Value
   80 │          ✕ ← ANOMALY! (Outside the band)
      │    ╱ ─ ─ ─ ─ ─ ─ ─ ─ ─ ╲   ← Upper boundary
   60 │  ╱  ┌─────────────────┐  ╲
      │ ╱   │  SAFE ZONE      │   ╲
   40 │╱    │  (Normal data   │    ╲
      │     │   lives here)   │
   20 │     └─────────────────┘      ← Lower boundary
      └──────────────────────────────
        Time →

  If a data point falls OUTSIDE the band, it's flagged as an anomaly.
```

---

## Lab: Let's Build a Moving Average Detector

### Step 1: Moving Average for CPU (One Metric)

Let's start simple — just one metric (CPU) — so you can see exactly how it works.

```python
import pandas as pd    # pandas = library for working with spreadsheets in Python
import numpy as np     # numpy  = library for math operations on lists of numbers

# ───────────────────────────────────────────────────────
# STEP 1: Load our server data
# ───────────────────────────────────────────────────────
df = pd.read_csv('server_telemetry.csv')

# ───────────────────────────────────────────────────────
# STEP 2: Set our parameters
# ───────────────────────────────────────────────────────
window_size = 10    # Look at the last 10 readings (= 50 minutes of server data)
n_std = 2           # Flag anything 2 standard deviations away from the moving average

# ───────────────────────────────────────────────────────
# STEP 3: Calculate the moving average for CPU
# ───────────────────────────────────────────────────────
# .rolling(window=10) means: "for each row, look at the 10 rows before it"
# .mean() calculates the average of those 10 rows
# Think of it as: "What has CPU been doing for the last 50 minutes?"
df['cpu_rolling_mean'] = df['cpu_percent'].rolling(window=window_size).mean()

# .std() calculates the standard deviation of those same 10 rows
# Think of it as: "How much has CPU been bouncing around recently?"
df['cpu_rolling_std'] = df['cpu_percent'].rolling(window=window_size).std()

# ───────────────────────────────────────────────────────
# STEP 4: Calculate the upper and lower boundaries of our "safe zone"
# ───────────────────────────────────────────────────────
# Upper boundary = moving average + (2 × recent std dev)
# Lower boundary = moving average - (2 × recent std dev)
# Anything outside these boundaries is suspicious!
df['cpu_upper_band'] = df['cpu_rolling_mean'] + (n_std * df['cpu_rolling_std'])
df['cpu_lower_band'] = df['cpu_rolling_mean'] - (n_std * df['cpu_rolling_std'])

# ───────────────────────────────────────────────────────
# STEP 5: Flag anomalies
# ───────────────────────────────────────────────────────
# np.where works like an IF statement:
#   IF cpu is above the upper band OR below the lower band → flag as -1 (Anomaly)
#   ELSE → flag as 1 (Normal)
df['cpu_ma_anomaly'] = np.where(
    (df['cpu_percent'] > df['cpu_upper_band']) | (df['cpu_percent'] < df['cpu_lower_band']),
    -1,  # Anomaly
    1    # Normal
)

# The first 9 rows don't have enough history for a 10-row average, so we skip them
# .dropna() removes rows that have missing values (NaN)
df_valid = df.dropna()

n_anomalies = (df_valid['cpu_ma_anomaly'] == -1).sum()
print(f"🔴 Moving Average anomalies (CPU): {n_anomalies}")
print(f"🔵 Normal data points: {len(df_valid) - n_anomalies}")
```

Expected Output:
```text
🔴 Moving Average anomalies (CPU): 45
🔵 Normal data points: 946
```

---

### Step 2: Apply to ALL Four Metrics

Now let's do the same thing for CPU, Memory, Network, and Disk — all at once:

```python
features = ['cpu_percent', 'memory_percent', 'network_mbps', 'disk_iops']

# ───────────────────────────────────────────────────────
# Run the same steps for each metric
# ───────────────────────────────────────────────────────
for col in features:
    # Calculate moving average and standard deviation for this metric
    df[f'{col}_rolling_mean'] = df[col].rolling(window=window_size).mean()
    df[f'{col}_rolling_std'] = df[col].rolling(window=window_size).std()

    # Calculate upper and lower safe boundaries
    df[f'{col}_upper'] = df[f'{col}_rolling_mean'] + (n_std * df[f'{col}_rolling_std'])
    df[f'{col}_lower'] = df[f'{col}_rolling_mean'] - (n_std * df[f'{col}_rolling_std'])

    # Flag anomalies for this metric
    df[f'{col}_ma_anomaly'] = np.where(
        (df[col] > df[f'{col}_upper']) | (df[col] < df[f'{col}_lower']),
        -1, 1
    )

# ───────────────────────────────────────────────────────
# Combine: if ANY metric is flagged, the whole row is an anomaly
# ───────────────────────────────────────────────────────
ma_anomaly_cols = [f'{col}_ma_anomaly' for col in features]
df['ma_anomaly'] = df[ma_anomaly_cols].apply(
    lambda row: -1 if any(row == -1) else 1,
    axis=1  # axis=1 = check each row
)

df_valid = df.dropna()
n_total = (df_valid['ma_anomaly'] == -1).sum()
print(f"\n🔴 Total Moving Average anomalies (all metrics): {n_total}")
```

### Step 3: Visualize with Rolling Bands

This creates a beautiful 4-panel chart showing raw data, the moving average line, and the safe band:

```python
import matplotlib.pyplot as plt

df_valid = df.dropna().reset_index(drop=True)

# Create 4 stacked charts (one for each metric)
fig, axes = plt.subplots(4, 1, figsize=(16, 14), sharex=True)
fig.suptitle('Moving Average Anomaly Detection (Window=10, Band=2σ)', fontsize=16, fontweight='bold')

for ax, col in zip(axes, features):
    # Draw the raw data as a thin blue line
    ax.plot(df_valid.index, df_valid[col], color='steelblue', alpha=0.6, linewidth=0.8, label='Raw Data')
    # Draw the moving average as a thick navy line
    ax.plot(df_valid.index, df_valid[f'{col}_rolling_mean'], color='navy', linewidth=1.5, label='Moving Avg')
    # Draw the safe band as a shaded area
    ax.fill_between(
        df_valid.index,
        df_valid[f'{col}_lower'],
        df_valid[f'{col}_upper'],
        alpha=0.15, color='navy', label='Safe Zone (±2σ)'
    )
    # Mark anomalies as red X marks
    anom = df_valid[df_valid[f'{col}_ma_anomaly'] == -1]
    ax.scatter(anom.index, anom[col], c='red', s=30, marker='x', zorder=5, label='Anomaly')
    ax.set_ylabel(col)
    ax.legend(loc='upper right', fontsize=8)

axes[-1].set_xlabel('Data Point Index')
plt.tight_layout()
plt.savefig('moving_average_results.png', dpi=150)
plt.show()
print("📊 Plot saved to moving_average_results.png")
```

You should see 4 stacked time-series plots, each showing:
- The **raw data** (thin blue line bouncing around)
- The **moving average** (thick smooth navy line)
- The **safe zone** (shaded band around the moving average)
- **Red X marks** where data points break outside the safe zone

---

## Tuning: What Happens When You Change the Settings?

### Window Size: How Far Back Do We Look?

| Window Size | What Happens | Good For |
|---|---|---|
| **5** (25 min) | Very reactive — catches spikes fast, but also triggers on small bumps | Fast-changing metrics |
| **10** (50 min) | Balanced — good default for most server metrics | General use |
| **20** (100 min) | Smooth and stable — ignores short bumps | Slow-changing trends |
| **50** (250 min) | Very smooth — only catches major sustained shifts | Long-term trends |

### Experiment: See the Difference Yourself

```python
# Try different window sizes and see how many anomalies each one catches
print("Window Size Experiment (CPU only):")
print("=" * 45)
for w in [5, 10, 20, 50]:
    rolling_mean = df['cpu_percent'].rolling(window=w).mean()
    rolling_std = df['cpu_percent'].rolling(window=w).std()
    upper = rolling_mean + (2 * rolling_std)
    lower = rolling_mean - (2 * rolling_std)
    anomalies = ((df['cpu_percent'] > upper) | (df['cpu_percent'] < lower)).sum()
    print(f"  Window = {w:2d} → {anomalies} CPU anomalies detected")
```

Expected Output:
```text
Window Size Experiment (CPU only):
=============================================
  Window =  5 → 62 CPU anomalies detected
  Window = 10 → 45 CPU anomalies detected
  Window = 20 → 38 CPU anomalies detected
  Window = 50 → 28 CPU anomalies detected
```

**Key takeaway:** Larger windows = fewer anomalies. The trade-off is that you also miss real problems that happen quickly.

---

## Z-Score vs Moving Average: Quick Comparison

| | Z-Score (Lesson 03) | Moving Average (This Lesson) |
|---|---|---|
| **Compares against** | The overall average of ALL data | The average of the LAST 10 readings |
| **Best for** | Sudden, extreme spikes | Gradual trends and time-aware detection |
| **Weakness** | Can't handle "normal" changing over time | Misses the very first few data points (cold start) |
| **Speed** | Instant (one calculation) | Slightly slower (needs recent history) |

---

## What's Next

You now have three anomaly detection methods implemented:
1. **Isolation Forest** (AI/ML approach)
2. **Z-Score** (simple statistics)
3. **Moving Average** (time-aware statistics)

In the next lesson, we will **intentionally inject fake anomalies** (CPU spikes, memory leaks, disk fills) into the dataset and run all three detectors to see **which method catches each type of anomaly best!**
