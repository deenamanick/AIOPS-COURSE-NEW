# 02 — Isolation Forest

Isolation Forest is a machine learning algorithm designed to find anomalies (weird data points). Don't worry — you don't need to understand the math behind it. Think of it as a **smart assistant** that you train by showing it examples of normal server behavior, and then it tells you which data points look suspicious.

---

## Real-World Analogy: The Security Guard

Imagine a security guard watching people enter an office building every day. After a few weeks, the guard knows the "normal" pattern:
- Most people arrive between 8-9 AM wearing business clothes.
- They badge in and walk straight to the elevators.

One day, someone arrives at 3 AM wearing a ski mask and tries every door. The guard doesn't need a rule that says "alert on ski masks at 3 AM" — the person just **stands out** from everyone else because they're *few and different*.

That's exactly how Isolation Forest works:
1. It studies all the data and learns what "normal" looks like.
2. Anything that looks **few and different** gets flagged as an anomaly.

---

## How It Works (Simple Version)

The algorithm randomly picks a metric (say CPU) and draws a line through it. It keeps drawing random lines to split the data into smaller and smaller groups.

- **Normal data points** are clustered together, so it takes MANY splits to isolate one.
- **Anomalies** are sitting far away from everyone else, so it takes very FEW splits to isolate them.

```
  Normal Point (takes 5 splits):      Anomaly (takes only 2 splits):

       ┌───────┐                             ┌───────┐
       │ Split  │                             │ Split  │
       ├───┬───┤                              ├───┬───┤
       │   │   │                              │   │ 🔴 ← Found it in just 2 splits!
       ├─┬─┤   │                              │   │
       │ │ │   │                              │   │
       │ 🔵│   │ ← Took 5 splits to find      │   │
```

**Bottom line:** If a data point is easy to isolate, it's probably an anomaly.

---

## Lab: Training Isolation Forest on Server Data

### Step 1: Look at the Data First

Before training any AI, let's peek at our data to understand what we're working with:

```python
import pandas as pd    # pandas = a library for working with spreadsheets in Python

# Load the CSV file into a "DataFrame" — think of it as opening a spreadsheet
df = pd.read_csv('server_telemetry.csv')

# .head(10) shows the first 10 rows so we can see what the data looks like
print(df.head(10))

# .shape tells us how many rows and columns: (rows, columns)
print(f"\nDataset shape: {df.shape}")

# .describe() prints a summary: average, min, max, etc. for each column
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

Notice the `min` and `max` values — CPU goes up to 99% and Disk I/O goes up to 1850! Those extreme values are likely the anomalies we want to find.

### Step 2: Train the AI Model

```python
import pandas as pd    # pandas = spreadsheet library
import numpy as np     # numpy  = math library
from sklearn.ensemble import IsolationForest  # The AI algorithm we're going to use

# ───────────────────────────────────────────────────────
# STEP 1: Load data
# ───────────────────────────────────────────────────────
df = pd.read_csv('server_telemetry.csv')

# ───────────────────────────────────────────────────────
# STEP 2: Pick the columns (metrics) we want the AI to analyze
# ───────────────────────────────────────────────────────
# We skip 'timestamp' because the AI only needs numbers, not dates
features = ['cpu_percent', 'memory_percent', 'network_mbps', 'disk_iops']

# Create a smaller table with just those 4 columns
X = df[features]

# ───────────────────────────────────────────────────────
# STEP 3: Create and configure the AI model
# ───────────────────────────────────────────────────────
model = IsolationForest(
    n_estimators=100,       # Build 100 random trees (more trees = more accurate)
    contamination=0.05,     # Tell the AI: "about 5% of this data is probably bad"
    random_state=42,        # Use a fixed random seed so everyone gets the same results
    n_jobs=-1               # Use all CPU cores for speed
)

# ───────────────────────────────────────────────────────
# STEP 4: Train the model (teach it what "normal" looks like)
# ───────────────────────────────────────────────────────
# .fit() is like showing the security guard thousands of examples
model.fit(X)

# ───────────────────────────────────────────────────────
# STEP 5: Ask the model to grade every data point
# ───────────────────────────────────────────────────────
# .predict() returns:
#    1  = "This looks normal"
#   -1  = "This looks anomalous (suspicious)"
df['anomaly'] = model.predict(X)

# .decision_function() returns a raw "confidence score" for each row
# More negative = more anomalous
df['anomaly_score'] = model.decision_function(X)

# ───────────────────────────────────────────────────────
# STEP 6: Count the results
# ───────────────────────────────────────────────────────
n_anomalies = (df['anomaly'] == -1).sum()    # How many rows got -1?
n_normal = (df['anomaly'] == 1).sum()        # How many rows got 1?
print(f"\n✅ Normal points: {n_normal}")
print(f"🔴 Anomalies detected: {n_anomalies}")
```

Expected Output:
```text
✅ Normal points: 950
🔴 Anomalies detected: 50
```

### Understanding the Settings

| Setting | Value | What It Means (Plain English) |
|---|---|---|
| `n_estimators` | 100 | Build 100 random trees. More trees = more stable results (like asking 100 security guards instead of 1). |
| `contamination` | 0.05 | "I expect about 5% of my data to be bad." This controls how sensitive the AI is. |
| `random_state` | 42 | Lock the randomness so every student gets identical results. |
| `n_jobs` | -1 | Use all CPU cores on your computer for faster training. |

### Step 3: Visualize the Results

Let's plot our results to SEE where the anomalies are:

```python
import matplotlib.pyplot as plt

# Split our data into two groups: normal and anomalous
normal = df[df['anomaly'] == 1]       # All rows where anomaly == 1
anomalies = df[df['anomaly'] == -1]   # All rows where anomaly == -1

# Create a 2x2 grid of scatter plots (4 charts)
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Isolation Forest Anomaly Detection — Server Telemetry', fontsize=16, fontweight='bold')

# We'll plot 4 pairs of metrics to see anomalies from different angles
plot_pairs = [
    ('cpu_percent', 'memory_percent', 'CPU vs Memory'),
    ('cpu_percent', 'network_mbps', 'CPU vs Network'),
    ('memory_percent', 'disk_iops', 'Memory vs Disk I/O'),
    ('network_mbps', 'disk_iops', 'Network vs Disk I/O'),
]

for ax, (x_col, y_col, title) in zip(axes.flat, plot_pairs):
    # Plot normal points as small blue dots
    ax.scatter(normal[x_col], normal[y_col], c='steelblue', s=10, alpha=0.5, label='Normal')
    # Plot anomalies as big red X marks (so they stand out)
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
- **Blue dots** = normal data, all clustered together in the center.
- **Red X marks** = anomalies, scattered at the edges or in unusual positions.

### Step 4: Inspect the Top Anomalies

Let's look at WHAT the AI flagged. Which server readings does it think are the most suspicious?

```python
# Sort anomalies by their score (most anomalous first) and show the top 10
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

Notice how the AI detected:
- **High everything** (CPU 99%, Memory 95%, Disk 1850) → likely a runaway process eating all resources
- **High CPU but low network** → possibly a compute-bound attack (something is burning CPU but not doing any network I/O)
- **Low everything** → possibly a service that has stopped processing entirely

---

## Tuning: The Contamination Parameter

The `contamination` setting is the single most important knob to turn. It tells the AI: *"What percentage of my data do you think is bad?"*

| Contamination | What the AI Does | When to Use It |
|---|---|---|
| **0.01 (1%)** | Very careful — only flags the most extreme outliers | Production systems where false alarms are expensive |
| **0.05 (5%)** | Balanced — good starting point | General server monitoring |
| **0.10 (10%)** | Aggressive — flags lots of data as suspicious | When you're exploring and want to catch everything |

### Experiment: Try Different Values

```python
# Run the AI 3 times with different contamination settings
print("Contamination Experiment:")
print("=" * 55)
for c in [0.01, 0.05, 0.10]:
    model = IsolationForest(contamination=c, random_state=42)
    model.fit(X)
    predictions = model.predict(X)
    n_anom = (predictions == -1).sum()
    print(f"  contamination={c:.2f} → {n_anom} anomalies detected ({n_anom/len(X)*100:.1f}%)")
```

Expected Output:
```text
Contamination Experiment:
=======================================================
  contamination=0.01 → 10 anomalies detected (1.0%)
  contamination=0.05 → 50 anomalies detected (5.0%)
  contamination=0.10 → 100 anomalies detected (10.0%)
```

**Key takeaway:** Higher contamination = the AI flags more data as suspicious. Lower = it only flags the most extreme cases.

---

## What's Next

Isolation Forest is powerful but can feel like a "black box" — it tells you WHAT is anomalous, but not exactly WHY. In the next lesson, we will implement **Z-Score anomaly detection** — a much simpler technique based on basic math that you can understand completely. You'll then compare the two approaches.
