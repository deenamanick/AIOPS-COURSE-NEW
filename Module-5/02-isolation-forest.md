# 02 — Isolation Forest

The Isolation Forest is a powerful unsupervised machine learning algorithm specifically designed for anomaly detection. Unlike traditional methods that try to profile "normal" data, Isolation Forest takes the opposite approach: it directly isolates anomalies by exploiting the fact that **anomalies are few and different**.

---

## How Isolation Forest Works

The intuition behind Isolation Forest is elegant:

1. **Random Splits**: The algorithm randomly selects a feature (e.g., CPU) and a random split value within that feature's range.
2. **Tree Building**: It recursively partitions the data using these random splits, building a binary tree.
3. **Path Length**: Anomalies, being "few and different," require **fewer splits** to isolate from the rest of the data. Normal points, being dense and clustered, require **more splits**.
4. **Anomaly Score**: Points with shorter average path lengths across many trees are scored as more anomalous.

```
  Normal Point (deep in tree):          Anomaly (near root):

       ┌───────┐                             ┌───────┐
       │ Split  │                             │ Split  │
       ├───┬───┤                              ├───┬───┤
       │   │   │                              │   │ 🔴 ← Isolated in 2 splits!
       ├─┬─┤   │                              │   │
       │ │ │   │                              │   │
       │ 🔵│   │ ← Isolated in 5 splits       │   │
       │  │    │                              │   │
```

---

## Lab: Training Isolation Forest on Telemetry Data

### Step 1: Explore the Dataset

In the `lab/` directory, there is a CSV file named `server_telemetry.csv` containing 1000 rows of simulated server metrics:

```python
import pandas as pd

# Load the CSV file into a pandas DataFrame (which is like a spreadsheet in Python)
df = pd.read_csv('server_telemetry.csv')

# .head(10) prints the first 10 rows of the spreadsheet so we can peek at the data
print(df.head(10))
# .shape tells us the number of rows and columns (e.g., 1000 rows, 5 columns)
print(f"\nDataset shape: {df.shape}")
# .describe() automatically calculates mean, min, max, and standard deviation for every column
print(f"\nColumn statistics:\n{df.describe()}")
```

Expected Output:
```text
   timestamp    cpu_percent  memory_percent  network_mbps  disk_iops
0  2024-01-01   45.2         62.1            480.3         210.5
1  2024-01-01   47.8         63.4            495.1         205.8
2  2024-01-01   44.1         61.8            510.2         198.3
...

Dataset shape: (1000, 5)

Column statistics:
       cpu_percent  memory_percent  network_mbps  disk_iops
mean     48.52        63.18           492.31        208.42
std       8.74        10.21            45.82         32.15
min      12.30        28.40           180.50         85.20
max      99.10        97.80           890.40       1850.30
```

Notice the `min` and `max` values — the dataset contains some extreme values that are likely anomalies.

### Step 2: Train the Isolation Forest Model

```python
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

# Load data into our spreadsheet
df = pd.read_csv('server_telemetry.csv')

# Select the 4 feature columns we want the AI to analyze (exclude the timestamp)
features = ['cpu_percent', 'memory_percent', 'network_mbps', 'disk_iops']
# X is a smaller spreadsheet containing ONLY those 4 columns (AI algorithms need numbers only)
X = df[features]

# Train Isolation Forest (AI algorithm)
model = IsolationForest(
    n_estimators=100,       # Number of trees in the forest
    contamination=0.05,     # Tell the AI to expect 5% of data points to be anomalies
    random_state=42,        # Set a random seed so results are identical every time
    n_jobs=-1               # Use all CPU cores for faster processing
)

# .fit(X) tells the AI to study the data and learn what "normal" looks like
model.fit(X)

# .predict(X) asks the AI to grade the data: 1 = normal, -1 = anomaly
df['anomaly'] = model.predict(X)
# .decision_function(X) gives us a raw score (negative numbers indicate anomalies)
df['anomaly_score'] = model.decision_function(X)

# Count how many rows were flagged as -1 (anomaly) and 1 (normal)
n_anomalies = (df['anomaly'] == -1).sum()
n_normal = (df['anomaly'] == 1).sum()
print(f"\n✅ Normal points: {n_normal}")
print(f"🔴 Anomalies detected: {n_anomalies}")
```

Expected Output:
```text
✅ Normal points: 950
🔴 Anomalies detected: 50
```

### Understanding the Parameters

| Parameter | Value | Purpose |
|---|---|---|
| `n_estimators` | 100 | Number of isolation trees. More trees = more stable predictions. |
| `contamination` | 0.05 | Tells the model to expect 5% of data as anomalous. This directly controls the threshold. |
| `random_state` | 42 | Ensures reproducible results across runs. |
| `n_jobs` | -1 | Parallelizes training across all CPU cores. |

### Step 3: Visualize the Results

```python
import matplotlib.pyplot as plt
import matplotlib

# Separate normal and anomalous points
normal = df[df['anomaly'] == 1]
anomalies = df[df['anomaly'] == -1]

# Create a 2x2 grid of scatter plots
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Isolation Forest Anomaly Detection — Server Telemetry', fontsize=16, fontweight='bold')

plot_pairs = [
    ('cpu_percent', 'memory_percent', 'CPU vs Memory'),
    ('cpu_percent', 'network_mbps', 'CPU vs Network'),
    ('memory_percent', 'disk_iops', 'Memory vs Disk I/O'),
    ('network_mbps', 'disk_iops', 'Network vs Disk I/O'),
]

for ax, (x_col, y_col, title) in zip(axes.flat, plot_pairs):
    ax.scatter(normal[x_col], normal[y_col], c='steelblue', s=10, alpha=0.5, label='Normal')
    ax.scatter(anomalies[x_col], anomalies[y_col], c='red', s=40, marker='x', label='Anomaly')
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title)
    ax.legend(loc='upper right', fontsize=8)

plt.tight_layout()
plt.savefig('isolation_forest_results.png', dpi=150)
plt.show()
print("📊 Plot saved to isolation_forest_results.png")
```

You should see a 2x2 grid where:
- **Blue dots** represent normal telemetry data points clustered together.
- **Red X marks** represent anomalies scattered at the edges or in unusual positions.

### Step 4: Inspect the Anomalies

Let's examine what the model flagged:

```python
# Show the most anomalous data points
top_anomalies = df[df['anomaly'] == -1].sort_values('anomaly_score').head(10)
print("\n🔴 Top 10 Most Anomalous Data Points:")
print(top_anomalies[['timestamp', 'cpu_percent', 'memory_percent', 'network_mbps', 'disk_iops', 'anomaly_score']].to_string(index=False))
```

Expected Output:
```text
🔴 Top 10 Most Anomalous Data Points:
    timestamp  cpu_percent  memory_percent  network_mbps  disk_iops  anomaly_score
  2024-01-15        99.1           95.2         890.4     1850.3        -0.312
  2024-01-08        97.8           92.1          85.2      180.5        -0.287
  2024-01-22        12.3           28.4         180.5       85.2        -0.265
  ...
```

Notice how the model detected:
- **High everything** (CPU 99%, Memory 95%, Disk 1850) — likely a runaway process
- **High CPU but low network** — possibly a compute-bound attack
- **Low everything** — possibly a service that has stopped processing

---

## The Contamination Parameter

The `contamination` parameter is the most important hyperparameter to tune. It tells the model what percentage of your data you expect to be anomalous.

| Contamination | Effect | When to Use |
|---|---|---|
| 0.01 (1%) | Very conservative. Only flags extreme outliers. | High-stakes production: you want zero false alarms. |
| 0.05 (5%) | Balanced. Good starting point for most workloads. | General monitoring: acceptable false positive rate. |
| 0.10 (10%) | Aggressive. Flags many data points as anomalous. | Exploration: you want to investigate as many potential issues as possible. |

### Experiment: Varying Contamination

```python
for c in [0.01, 0.05, 0.10]:
    model = IsolationForest(contamination=c, random_state=42)
    model.fit(X)
    preds = model.predict(X)
    n_anom = (preds == -1).sum()
    print(f"Contamination={c:.2f} → {n_anom} anomalies detected ({n_anom/len(X)*100:.1f}%)")
```

Expected Output:
```text
Contamination=0.01 → 10 anomalies detected (1.0%)
Contamination=0.05 → 50 anomalies detected (5.0%)
Contamination=0.10 → 100 anomalies detected (10.0%)
```

---

## What's Next

Isolation Forest is powerful but can feel like a "black box." In the next lesson, we will implement **Z-score anomaly detection** — a simpler, more interpretable approach that uses basic statistics. You'll then compare the results side by side.
