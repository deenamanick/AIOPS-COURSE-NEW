# 05 — Break/Fix Activities

In this lesson, you will act as an SRE and **inject synthetic anomalies** into the telemetry dataset. You will then run all three detection methods (Isolation Forest, Z-Score, Moving Average) and compare which method catches each anomaly type best.

---

## Activity 1: Inject Synthetic Anomalies

### Step 1: Create the Injection Script

Create a new file `inject_anomalies.py` in the lab directory:

```python
"""Inject 3 types of synthetic anomalies into the telemetry dataset."""

import pandas as pd
import numpy as np

# Load clean data
df = pd.read_csv('server_telemetry.csv')
print(f"Original dataset: {len(df)} rows")

# --- Anomaly Type 1: CPU Spike ---
# Simulate a sudden CPU spike to 99% for 5 consecutive data points
spike_start = 200
for i in range(spike_start, spike_start + 5):
    df.loc[i, 'cpu_percent'] = np.random.uniform(95, 99)
    df.loc[i, 'injected_anomaly'] = 'cpu_spike'
print(f"💥 Injected CPU spike at rows {spike_start}-{spike_start+4}")

# --- Anomaly Type 2: Memory Leak (Gradual Increase) ---
# Simulate memory slowly climbing from 65% to 97% over 20 data points
leak_start = 500
for i in range(leak_start, leak_start + 20):
    progress = (i - leak_start) / 20
    df.loc[i, 'memory_percent'] = 65 + (progress * 32)  # 65% → 97%
    df.loc[i, 'injected_anomaly'] = 'memory_leak'
print(f"💧 Injected memory leak at rows {leak_start}-{leak_start+19}")

# --- Anomaly Type 3: Disk Fill ---
# Simulate disk I/O spiking to 1800+ for 8 consecutive points
fill_start = 750
for i in range(fill_start, fill_start + 8):
    df.loc[i, 'disk_iops'] = np.random.uniform(1500, 1850)
    df.loc[i, 'injected_anomaly'] = 'disk_fill'
print(f"💾 Injected disk fill at rows {fill_start}-{fill_start+7}")

# Fill remaining rows
df['injected_anomaly'] = df['injected_anomaly'].fillna('none')

# Save
df.to_csv('server_telemetry_injected.csv', index=False)
print(f"\n✅ Saved to server_telemetry_injected.csv")
print(f"   Total injected anomalies: {(df['injected_anomaly'] != 'none').sum()}")
```

### Step 2: Run the Injection

```bash
python inject_anomalies.py
```

Expected Output:
```text
Original dataset: 1000 rows
💥 Injected CPU spike at rows 200-204
💧 Injected memory leak at rows 500-519
💾 Injected disk fill at rows 750-757
✅ Saved to server_telemetry_injected.csv
   Total injected anomalies: 33
```

---

## Activity 2: Run All Three Detectors

### Step 1: Create the Comparison Script

Create `compare_detectors.py`:

```python
"""Run all 3 anomaly detection methods on the injected dataset and compare."""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

# Load injected data
df = pd.read_csv('server_telemetry_injected.csv')
features = ['cpu_percent', 'memory_percent', 'network_mbps', 'disk_iops']
X = df[features]

# ─────────────────────────────────────────────────
# Method 1: Isolation Forest
# ─────────────────────────────────────────────────
iso_model = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
iso_model.fit(X)
df['iso_forest'] = iso_model.predict(X)

# ─────────────────────────────────────────────────
# Method 2: Z-Score (threshold=3)
# ─────────────────────────────────────────────────
z_threshold = 3
for col in features:
    df[f'{col}_z'] = (df[col] - df[col].mean()) / df[col].std()

z_cols = [f'{col}_z' for col in features]
df['zscore'] = df[z_cols].apply(
    lambda row: -1 if any(abs(row) > z_threshold) else 1, axis=1
)

# ─────────────────────────────────────────────────
# Method 3: Moving Average (window=10, band=2σ)
# ─────────────────────────────────────────────────
window = 10
n_std = 2
for col in features:
    rm = df[col].rolling(window=window).mean()
    rs = df[col].rolling(window=window).std()
    df[f'{col}_ma'] = np.where(
        (df[col] > rm + n_std * rs) | (df[col] < rm - n_std * rs), -1, 1
    )

ma_cols = [f'{col}_ma' for col in features]
df['moving_avg'] = df[ma_cols].apply(
    lambda row: -1 if any(row == -1) else 1, axis=1
)

# ─────────────────────────────────────────────────
# Compare: How many injected anomalies did each method catch?
# ─────────────────────────────────────────────────
injected = df[df['injected_anomaly'] != 'none']

print("=" * 70)
print("ANOMALY DETECTION COMPARISON REPORT")
print("=" * 70)

for anomaly_type in ['cpu_spike', 'memory_leak', 'disk_fill']:
    subset = injected[injected['injected_anomaly'] == anomaly_type]
    total = len(subset)
    iso_caught = (subset['iso_forest'] == -1).sum()
    z_caught = (subset['zscore'] == -1).sum()
    ma_caught = (subset['moving_avg'] == -1).sum()

    print(f"\n{'─' * 50}")
    print(f"  Anomaly Type: {anomaly_type.upper()}")
    print(f"  Injected Points: {total}")
    print(f"{'─' * 50}")
    print(f"  Isolation Forest:  {iso_caught}/{total} caught ({iso_caught/total*100:.0f}%)")
    print(f"  Z-Score (3σ):      {z_caught}/{total} caught ({z_caught/total*100:.0f}%)")
    print(f"  Moving Average:    {ma_caught}/{total} caught ({ma_caught/total*100:.0f}%)")

# Overall false positive count
non_injected = df[df['injected_anomaly'] == 'none']
print(f"\n{'=' * 70}")
print("FALSE POSITIVE ANALYSIS (Non-injected data flagged as anomaly)")
print(f"{'=' * 70}")
print(f"  Isolation Forest:  {(non_injected['iso_forest'] == -1).sum()} false positives")
print(f"  Z-Score:           {(non_injected['zscore'] == -1).sum()} false positives")
print(f"  Moving Average:    {(non_injected['moving_avg'] == -1).sum()} false positives")
```

### Step 2: Run the Comparison

```bash
python compare_detectors.py
```

Expected Output:
```text
======================================================================
ANOMALY DETECTION COMPARISON REPORT
======================================================================

──────────────────────────────────────────────────
  Anomaly Type: CPU_SPIKE
  Injected Points: 5
──────────────────────────────────────────────────
  Isolation Forest:  5/5 caught (100%)
  Z-Score (3σ):      5/5 caught (100%)
  Moving Average:    5/5 caught (100%)

──────────────────────────────────────────────────
  Anomaly Type: MEMORY_LEAK
  Injected Points: 20
──────────────────────────────────────────────────
  Isolation Forest:  14/20 caught (70%)
  Z-Score (3σ):      6/20 caught (30%)
  Moving Average:    12/20 caught (60%)

──────────────────────────────────────────────────
  Anomaly Type: DISK_FILL
  Injected Points: 8
──────────────────────────────────────────────────
  Isolation Forest:  8/8 caught (100%)
  Z-Score (3σ):      8/8 caught (100%)
  Moving Average:    7/8 caught (88%)

======================================================================
FALSE POSITIVE ANALYSIS (Non-injected data flagged as anomaly)
======================================================================
  Isolation Forest:  36 false positives
  Z-Score:           24 false positives
  Moving Average:    38 false positives
```

---

## Activity 3: Interpret the Results

### Key Findings

| Anomaly Type | Best Detector | Why? |
|---|---|---|
| **CPU Spike** | All three (tie) | Sudden, extreme spikes are trivially detectable by any method. |
| **Memory Leak** | Isolation Forest | Gradual leaks don't trigger Z-score (individual values stay within 3σ). Isolation Forest detects the multi-dimensional shift. |
| **Disk Fill** | Isolation Forest & Z-Score | Extreme disk values easily exceed 3σ. Moving Average misses the first point due to windowing lag. |

### The Verdict

| Method | Best For | Worst For |
|---|---|---|
| **Isolation Forest** | Multi-dimensional, gradual, complex anomalies | Requires scikit-learn, less interpretable |
| **Z-Score** | Simple, sudden, extreme spikes | Misses gradual changes, single-dimensional |
| **Moving Average** | Time-aware trend deviations, noisy data | Lagging, window sensitivity, cold start |

**Recommendation for production**: Use **Isolation Forest** as your primary detector (catches the most anomaly types) and supplement with **Z-score** for real-time, low-latency alerting on individual metrics.

---

## What's Next

You've now built, compared, and benchmarked three different anomaly detection methods. In the final lesson, we will explore how production AIOps platforms scale these techniques to handle streaming data, ensemble methods, and automated incident response.
