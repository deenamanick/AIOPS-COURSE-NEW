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
