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

# -------------------------------------------------------------------
# STEP 1: Load our normal data into a DataFrame (spreadsheet)
# -------------------------------------------------------------------
# pd.read_csv reads a CSV file and converts it into a pandas DataFrame object
df = pd.read_csv('server_telemetry.csv')
print(f"Original dataset: {len(df)} rows")

# We add a new column to our spreadsheet called 'injected_anomaly' and set every row to 'none'
df['injected_anomaly'] = 'none'

# -------------------------------------------------------------------
# STEP 2: Manually inject large, obvious anomalies
# -------------------------------------------------------------------

# --- Anomaly Type 1: CPU Spike ---
# We want to simulate a severe CPU spike starting at row 200
spike_start = 200
# range(200, 205) will loop 5 times (rows 200, 201, 202, 203, 204)
for i in range(spike_start, spike_start + 5):
    # df.loc[row, column] targets exactly one cell to overwrite
    df.loc[i, 'cpu_percent'] = np.random.uniform(95, 99)
    # Label this row so we can track it later
    df.loc[i, 'injected_anomaly'] = 'cpu_spike'
print(f"💥 Injected CPU spike at rows {spike_start}-{spike_start+4}")

# --- Anomaly Type 2: Memory Leak (Gradual Increase) ---
# A memory leak isn't a sudden spike; memory usage slowly climbs until it crashes.
leak_start = 500
# We will simulate the leak over 20 time periods (rows 500 to 519)
for i in range(leak_start, leak_start + 20):
    # Calculate how far along we are in the 20-step leak (from 0.0 to 1.0)
    progress = (i - leak_start) / 20
    # Gradually increase memory from a baseline of 65% up to ~97%
    df.loc[i, 'memory_percent'] = 65 + (progress * 32)
    df.loc[i, 'injected_anomaly'] = 'memory_leak'
print(f"💧 Injected memory leak at rows {leak_start}-{leak_start+19}")

# --- Anomaly Type 3: Disk Fill ---
# Simulating a massive burst of disk writes
fill_start = 750
for i in range(fill_start, fill_start + 8):
    df.loc[i, 'disk_iops'] = np.random.uniform(1500, 1850)
    df.loc[i, 'injected_anomaly'] = 'disk_fill'
print(f"💾 Injected disk fill at rows {fill_start}-{fill_start+7}")

# Fill remaining rows
df['injected_anomaly'] = df['injected_anomaly'].fillna('none')

# -------------------------------------------------------------------
# STEP 3: Save the contaminated dataset
# -------------------------------------------------------------------
# Save the new version of our table to a new CSV file
df.to_csv('server_telemetry_injected.csv', index=False)
print(f"\n✅ Saved to server_telemetry_injected.csv")

# Count how many rows do NOT have 'none' in the anomaly column
total_injected = (df['injected_anomaly'] != 'none').sum()
print(f"   Total injected anomalies: {total_injected}")
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

# -------------------------------------------------------------------
# SETUP: Load data and select the columns we care about
# -------------------------------------------------------------------
# Load the contaminated CSV into a pandas DataFrame (spreadsheet)
df = pd.read_csv('server_telemetry_injected.csv')

# These are the 4 "features" (metrics) the AI/algorithms will look at
features = ['cpu_percent', 'memory_percent', 'network_mbps', 'disk_iops']

# X is just a smaller spreadsheet containing ONLY those 4 columns (no timestamps or labels)
X = df[features]

# ─────────────────────────────────────────────────
# Method 1: Isolation Forest (Machine Learning)
# ─────────────────────────────────────────────────
# Isolation Forest is an AI algorithm that builds random decision trees.
# "Anomalies" are data points that get isolated very quickly because they look so different.
# contamination=0.05 tells the AI "Expect about 5% of this data to be bad."
iso_model = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)

# .fit(X) tells the AI to study the data and learn what "normal" looks like.
iso_model.fit(X)

# .predict(X) asks the AI to grade the data. It returns 1 for "Normal" and -1 for "Anomaly".
# We save these grades in a new column called 'iso_forest'
df['iso_forest'] = iso_model.predict(X)

# ─────────────────────────────────────────────────
# Method 2: Z-Score (Statistical thresholds)
# ─────────────────────────────────────────────────
# The Z-Score tells us how many "standard deviations" a number is away from the average.
# A Z-score of 3 means the data is EXTREMELY rare (like a 1-in-1000 event).
z_threshold = 3

for col in features:
    # Calculate Z-score: (Current Value - Average) / Standard Deviation
    df[f'{col}_z'] = (df[col] - df[col].mean()) / df[col].std()

z_cols = [f'{col}_z' for col in features]

# .apply() runs a custom function on every single row.
# If ANY of the 4 columns in a row have a Z-score greater than 3 (or less than -3), flag it as -1 (Anomaly)
df['zscore'] = df[z_cols].apply(
    lambda row: -1 if any(abs(row) > z_threshold) else 1, axis=1
)

# ─────────────────────────────────────────────────
# Method 3: Moving Average (Time-based thresholds)
# ─────────────────────────────────────────────────
# A moving average looks at the "recent past" to decide if the "present" is weird.
window = 10 # Look at the last 10 rows (which equals the last 50 minutes of data)
n_std = 2   # Flag anything that is 2 standard deviations away from that recent average

for col in features:
    # .rolling(window=10).mean() calculates the average of the last 10 rows
    rm = df[col].rolling(window=window).mean()
    # .rolling(window=10).std() calculates the standard deviation of the last 10 rows
    rs = df[col].rolling(window=window).std()
    
    # np.where(condition, true_value, false_value)
    # If the current value is way above or way below the recent average, flag it as -1 (Anomaly)
    df[f'{col}_ma'] = np.where(
        (df[col] > rm + n_std * rs) | (df[col] < rm - n_std * rs), -1, 1
    )

ma_cols = [f'{col}_ma' for col in features]
# Combine the results: if ANY metric in the row triggered the moving average, the whole row is an anomaly
df['moving_avg'] = df[ma_cols].apply(
    lambda row: -1 if any(row == -1) else 1, axis=1
)

# ─────────────────────────────────────────────────
# Compare: How many injected anomalies did each method catch?
# ─────────────────────────────────────────────────
# Filter our spreadsheet to ONLY show rows where we manually injected a fake anomaly
injected = df[df['injected_anomaly'] != 'none']

print("=" * 70)
print("ANOMALY DETECTION COMPARISON REPORT")
print("=" * 70)

for anomaly_type in ['cpu_spike', 'memory_leak', 'disk_fill']:
    # Filter down to just this specific type of anomaly
    subset = injected[injected['injected_anomaly'] == anomaly_type]
    total = len(subset)
    
    # Count how many times each method correctly guessed "-1" (Anomaly) for these rows
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

# -------------------------------------------------------------------
# FALSE POSITIVE ANALYSIS
# -------------------------------------------------------------------
# Filter our spreadsheet to ONLY show "normal" rows (where we didn't inject anything)
non_injected = df[df['injected_anomaly'] == 'none']
print(f"\n{'=' * 70}")
print("FALSE POSITIVE ANALYSIS (Normal data accidentally flagged as bad)")
print(f"{'=' * 70}")
# Count how many times the method WRONGLY guessed "-1" for normal data
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
