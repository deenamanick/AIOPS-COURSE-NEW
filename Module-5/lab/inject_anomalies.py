"""Inject 3 types of synthetic anomalies into the telemetry dataset."""

import pandas as pd
import numpy as np

# Load clean data
df = pd.read_csv('server_telemetry.csv')
print(f"Original dataset: {len(df)} rows")

# Initialize anomaly label column
df['injected_anomaly'] = 'none'

# --- Anomaly Type 1: CPU Spike ---
spike_start = 200
for i in range(spike_start, spike_start + 5):
    df.loc[i, 'cpu_percent'] = np.random.uniform(95, 99)
    df.loc[i, 'injected_anomaly'] = 'cpu_spike'
print(f"💥 Injected CPU spike at rows {spike_start}-{spike_start+4}")

# --- Anomaly Type 2: Memory Leak (Gradual Increase) ---
leak_start = 500
for i in range(leak_start, leak_start + 20):
    progress = (i - leak_start) / 20
    df.loc[i, 'memory_percent'] = 65 + (progress * 32)  # 65% → 97%
    df.loc[i, 'injected_anomaly'] = 'memory_leak'
print(f"💧 Injected memory leak at rows {leak_start}-{leak_start+19}")

# --- Anomaly Type 3: Disk Fill ---
fill_start = 750
for i in range(fill_start, fill_start + 8):
    df.loc[i, 'disk_iops'] = np.random.uniform(1500, 1850)
    df.loc[i, 'injected_anomaly'] = 'disk_fill'
print(f"💾 Injected disk fill at rows {fill_start}-{fill_start+7}")

# Save
df.to_csv('server_telemetry_injected.csv', index=False)
print(f"\n✅ Saved to server_telemetry_injected.csv")
print(f"   Total injected anomalies: {(df['injected_anomaly'] != 'none').sum()}")
