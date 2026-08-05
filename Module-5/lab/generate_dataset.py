"""Generate a synthetic server telemetry dataset with embedded anomalies."""

import numpy as np
import pandas as pd

np.random.seed(42)

n_samples = 1000

# Generate normal telemetry data
data = {
    'timestamp': pd.date_range('2024-01-01', periods=n_samples, freq='5min'),
    'cpu_percent': np.clip(np.random.normal(48, 8, n_samples), 5, 100),
    'memory_percent': np.clip(np.random.normal(63, 10, n_samples), 10, 100),
    'network_mbps': np.clip(np.random.normal(492, 45, n_samples), 50, 1000),
    'disk_iops': np.clip(np.random.normal(208, 32, n_samples), 20, 2000),
}

df = pd.DataFrame(data)

# Inject subtle anomalies into the dataset (approximately 5% of data)
anomaly_indices = np.random.choice(n_samples, size=50, replace=False)

for idx in anomaly_indices:
    anomaly_type = np.random.choice(['cpu_spike', 'memory_spike', 'network_drop', 'disk_surge'])
    if anomaly_type == 'cpu_spike':
        df.loc[idx, 'cpu_percent'] = np.random.uniform(92, 99)
    elif anomaly_type == 'memory_spike':
        df.loc[idx, 'memory_percent'] = np.random.uniform(88, 98)
    elif anomaly_type == 'network_drop':
        df.loc[idx, 'network_mbps'] = np.random.uniform(50, 180)
    elif anomaly_type == 'disk_surge':
        df.loc[idx, 'disk_iops'] = np.random.uniform(800, 1850)

# Round for cleanliness
df['cpu_percent'] = df['cpu_percent'].round(1)
df['memory_percent'] = df['memory_percent'].round(1)
df['network_mbps'] = df['network_mbps'].round(1)
df['disk_iops'] = df['disk_iops'].round(1)

df.to_csv('server_telemetry.csv', index=False)
print(f"✅ Generated server_telemetry.csv with {n_samples} rows and ~50 embedded anomalies")
print(f"   Columns: {list(df.columns)}")
print(f"\n{df.describe()}")
