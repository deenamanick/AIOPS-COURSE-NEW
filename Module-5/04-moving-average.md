# 04 — Moving Average Anomaly Detection

Z-score detection compares each data point against the **global** mean and standard deviation of the entire dataset. But in real-world telemetry, the "normal" baseline shifts over time. A server's CPU usage at 3 AM is very different from its usage at 3 PM. Moving average detection solves this by comparing each data point against a **local, sliding window** of recent values.

---

## What is a Moving Average?

A moving average (also called a "rolling mean") calculates the average of the last `N` data points at each step. It creates a **smoothed trend line** that filters out short-term noise while preserving the overall signal.

```
  Raw Data vs Moving Average (window=10):

  CPU %
  100│    ╱╲
   80│   ╱  ╲  ╱╲
   60│──╱────╲╱──╲──────────── Moving Average (smooth)
   40│ ╱           ╲╱╲
   20│╱               ╲╱
    0└────────────────────────
      0    200   400   600   800   1000
                  Data Points
```

An anomaly is flagged when the raw data point deviates from the moving average by more than a specified number of standard deviations (calculated within the same rolling window).

---

## Lab: Implementing Moving Average Detection

### Step 1: Calculate Rolling Statistics

```python
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('server_telemetry.csv')

# Parameters
window_size = 10    # Look at the last 10 data points
n_std = 2           # Flag if outside 2 rolling standard deviations

# Calculate rolling mean and standard deviation for CPU
df['cpu_rolling_mean'] = df['cpu_percent'].rolling(window=window_size, center=False).mean()
df['cpu_rolling_std'] = df['cpu_percent'].rolling(window=window_size, center=False).std()

# Define upper and lower bounds
df['cpu_upper_band'] = df['cpu_rolling_mean'] + (n_std * df['cpu_rolling_std'])
df['cpu_lower_band'] = df['cpu_rolling_mean'] - (n_std * df['cpu_rolling_std'])

# Flag anomalies: outside the rolling band
df['cpu_ma_anomaly'] = np.where(
    (df['cpu_percent'] > df['cpu_upper_band']) | (df['cpu_percent'] < df['cpu_lower_band']),
    -1, 1
)

# Drop NaN rows from the initial window
df_valid = df.dropna()
n_anomalies = (df_valid['cpu_ma_anomaly'] == -1).sum()
print(f"🔴 Moving Average anomalies (CPU, window={window_size}, {n_std}σ): {n_anomalies}")
```

Expected Output:
```text
🔴 Moving Average anomalies (CPU, window=10, 2σ): 45
```

### Step 2: Apply to All Metrics

```python
features = ['cpu_percent', 'memory_percent', 'network_mbps', 'disk_iops']

for col in features:
    df[f'{col}_rolling_mean'] = df[col].rolling(window=window_size).mean()
    df[f'{col}_rolling_std'] = df[col].rolling(window=window_size).std()
    df[f'{col}_upper'] = df[f'{col}_rolling_mean'] + (n_std * df[f'{col}_rolling_std'])
    df[f'{col}_lower'] = df[f'{col}_rolling_mean'] - (n_std * df[f'{col}_rolling_std'])
    df[f'{col}_ma_anomaly'] = np.where(
        (df[col] > df[f'{col}_upper']) | (df[col] < df[f'{col}_lower']),
        -1, 1
    )

# Combined anomaly: flag if ANY metric is outside its band
ma_anomaly_cols = [f'{col}_ma_anomaly' for col in features]
df['ma_anomaly'] = df[ma_anomaly_cols].apply(
    lambda row: -1 if any(row == -1) else 1, axis=1
)

df_valid = df.dropna()
n_total = (df_valid['ma_anomaly'] == -1).sum()
print(f"\n🔴 Total Moving Average anomalies (all metrics): {n_total}")
```

### Step 3: Visualize with Rolling Bands

```python
import matplotlib.pyplot as plt

df_valid = df.dropna().reset_index(drop=True)

fig, axes = plt.subplots(4, 1, figsize=(16, 14), sharex=True)
fig.suptitle('Moving Average Anomaly Detection (Window=10, Band=2σ)', fontsize=16, fontweight='bold')

for ax, col in zip(axes, features):
    ax.plot(df_valid.index, df_valid[col], color='steelblue', alpha=0.6, linewidth=0.8, label='Raw')
    ax.plot(df_valid.index, df_valid[f'{col}_rolling_mean'], color='navy', linewidth=1.5, label='Moving Avg')
    ax.fill_between(
        df_valid.index,
        df_valid[f'{col}_lower'],
        df_valid[f'{col}_upper'],
        alpha=0.15, color='navy', label='±2σ Band'
    )
    # Mark anomalies
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
- The **raw data** (thin blue line)
- The **moving average** (thick navy line)
- The **±2σ band** (shaded region)
- **Red X marks** where data points break outside the band

---

## Tuning the Moving Average

| Parameter | Effect of Increasing |
|---|---|
| `window_size` (10 → 50) | Smoother trend line, but slower to react to genuine changes. Longer windows "absorb" spikes. |
| `n_std` (2 → 3) | Wider bands = fewer anomalies flagged = fewer false positives but more missed detections. |

### Experiment: Window Size Impact

```python
for w in [5, 10, 20, 50]:
    rolling_mean = df['cpu_percent'].rolling(window=w).mean()
    rolling_std = df['cpu_percent'].rolling(window=w).std()
    upper = rolling_mean + (2 * rolling_std)
    lower = rolling_mean - (2 * rolling_std)
    anomalies = ((df['cpu_percent'] > upper) | (df['cpu_percent'] < lower)).sum()
    print(f"  Window={w:2d} → {anomalies} CPU anomalies")
```

Expected Output:
```text
  Window= 5 → 62 CPU anomalies
  Window=10 → 45 CPU anomalies
  Window=20 → 38 CPU anomalies
  Window=50 → 28 CPU anomalies
```

---

## Moving Average Limitations

| Limitation | Description |
|---|---|
| **Lag** | The moving average always trails behind the actual data. A sudden spike is only partially reflected in the rolling mean. |
| **Window Sensitivity** | Too small a window = noisy bands (many false positives). Too large = slow reaction to real changes. |
| **Cold Start** | The first `N-1` data points have no moving average (NaN), leaving a blind spot at the beginning. |

---

## What's Next

You now have three anomaly detection methods implemented. In the next lesson, we will **intentionally inject synthetic anomalies** into the dataset and run all three detectors side by side to see which method catches each type of anomaly best.
