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

# -------------------------------------------------------------------
# STEP 3: Save the contaminated dataset
# -------------------------------------------------------------------
# Save the new version of our table to a new CSV file
df.to_csv('server_telemetry_injected.csv', index=False)
print(f"\n✅ Saved to server_telemetry_injected.csv")

# Count how many rows do NOT have 'none' in the anomaly column
total_injected = (df['injected_anomaly'] != 'none').sum()
print(f"   Total injected anomalies: {total_injected}")
