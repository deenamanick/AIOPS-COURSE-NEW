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
