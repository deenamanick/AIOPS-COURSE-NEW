"""Generate a synthetic server telemetry dataset with embedded anomalies."""

import numpy as np
import pandas as pd

# Set a random seed so that every time a student runs this, they get the exact same "random" numbers.
np.random.seed(42)

n_samples = 1000

# -------------------------------------------------------------------
# STEP 1: Generate "normal" (healthy) server data
# -------------------------------------------------------------------
# numpy (np) is great at generating large lists of numbers quickly.
# np.random.normal(mean, standard_deviation, count) generates a list of numbers clustered around a "mean".
# np.clip(list, min_val, max_val) ensures none of our random numbers fall outside a realistic range.
data = {
    # pd.date_range creates a list of timestamps, spaced 5 minutes apart.
    'timestamp': pd.date_range('2024-01-01', periods=n_samples, freq='5min'),
    
    # CPU stays around 48%, never dropping below 5% or going above 100%
    'cpu_percent': np.clip(np.random.normal(48, 8, n_samples), 5, 100),
    
    # Memory stays around 63%
    'memory_percent': np.clip(np.random.normal(63, 10, n_samples), 10, 100),
    
    # Network traffic hovers around 492 Mbps
    'network_mbps': np.clip(np.random.normal(492, 45, n_samples), 50, 1000),
    
    # Disk Input/Output operations per second
    'disk_iops': np.clip(np.random.normal(208, 32, n_samples), 20, 2000),
}

# pandas (pd) DataFrames are basically just spreadsheets in Python.
# We are taking our dictionary of lists (data) and turning it into a neat table.
df = pd.DataFrame(data)

# -------------------------------------------------------------------
# STEP 2: Inject subtle anomalies into the dataset (approx 5% of data)
# -------------------------------------------------------------------
# Pick 50 random row numbers (indices) out of our 1000 rows where we will inject fake problems.
anomaly_indices = np.random.choice(n_samples, size=50, replace=False)

for idx in anomaly_indices:
    # Pick a random type of server issue
    anomaly_type = np.random.choice(['cpu_spike', 'memory_spike', 'network_drop', 'disk_surge'])
    
    # df.loc[row_index, column_name] lets us select a specific "cell" in our spreadsheet to edit it.
    if anomaly_type == 'cpu_spike':
        # Overwrite the normal CPU with a dangerously high number between 92% and 99%
        df.loc[idx, 'cpu_percent'] = np.random.uniform(92, 99)
    elif anomaly_type == 'memory_spike':
        df.loc[idx, 'memory_percent'] = np.random.uniform(88, 98)
    elif anomaly_type == 'network_drop':
        df.loc[idx, 'network_mbps'] = np.random.uniform(50, 180)
    elif anomaly_type == 'disk_surge':
        df.loc[idx, 'disk_iops'] = np.random.uniform(800, 1850)

# Round all the numbers to 1 decimal place so the CSV file looks cleaner
df['cpu_percent'] = df['cpu_percent'].round(1)
df['memory_percent'] = df['memory_percent'].round(1)
df['network_mbps'] = df['network_mbps'].round(1)
df['disk_iops'] = df['disk_iops'].round(1)

# Save our spreadsheet to a standard CSV file (index=False means we don't save the row numbers)
df.to_csv('server_telemetry.csv', index=False)

print(f"✅ Generated server_telemetry.csv with {n_samples} rows and ~50 embedded anomalies")
print(f"   Columns: {list(df.columns)}")
# df.describe() prints a handy statistical summary (mean, min, max) of our generated data
print(f"\n{df.describe()}")
