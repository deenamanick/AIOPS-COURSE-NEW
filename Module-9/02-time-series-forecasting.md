# 02 — Time-Series Forecasting

This lesson teaches you to load historical infrastructure metrics, fit a linear regression model, predict when each metric will reach its capacity limit, and visualize the forecast with matplotlib.

---

## The Problem

You have 30 days of disk usage data. The question: **"When will the disk reach 100%?"**

This is a regression problem. Given `(day, usage%)` pairs, fit a line `usage = slope × day + intercept` and solve for the day where `usage = 100`.

---

## Linear Regression Refresher

```text
y = mx + b

m = slope      (daily growth rate)
b = intercept  (starting value)
x = day number
y = predicted usage
```

Solving for exhaustion:

```text
100 = m × x_exhaustion + b
x_exhaustion = (100 - b) / m
```

If `m ≤ 0`, the metric is stable or declining—no exhaustion predicted.

---

## Lab: Forecast Disk, CPU, and Memory

### Step 1: Generate Training Data

The lab includes a data generator that creates realistic 30-day CSV files:

```bash
cd Module-9/lab
python3 scripts/generate_data.py
```

This creates three CSV files in `data/`:

```text
data/disk_usage.csv    — steady growth (~0.7%/day)
data/cpu_usage.csv     — noisy oscillation with slight upward trend
data/memory_usage.csv  — step increases on deploy days
```

Each CSV has two columns:

```csv
date,value
2026-07-01,42.1
2026-07-02,42.8
...
```

### Step 2: Run the Forecasting Engine

```bash
python3 scripts/forecast.py
```

The script loads each CSV, fits a linear regression, and outputs:

```text
═══════════════════════════════════════════════════════════════
  Disk Usage Forecast
═══════════════════════════════════════════════════════════════
  Current value:     63.2%
  Daily growth rate: +0.71%/day
  Days to 100%:      52 days
  Predicted date:    2026-09-27
  R² score:          0.97 (strong linear fit)

  ⚠️  ALERT: Disk will exhaust in < 60 days. Plan capacity expansion.
═══════════════════════════════════════════════════════════════
```

### Step 3: Visualize

The script generates plots in `output/`:

```text
output/disk_forecast.png
output/cpu_forecast.png
output/memory_forecast.png
```

Each plot shows:

- Blue dots: actual daily values
- Red line: fitted regression line
- Red dashed vertical line: predicted exhaustion date
- Green band: safe zone (< 80%)
- Yellow band: warning zone (80–90%)
- Red band: critical zone (> 90%)

---

## The Forecasting Script

Core logic from `scripts/forecast.py`:

```python
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta

def forecast_exhaustion(dates, values, limit=100.0):
    """Fit linear regression and predict when the metric hits the limit."""
    # Convert dates to day numbers
    base = dates[0]
    X = np.array([(d - base).days for d in dates]).reshape(-1, 1)
    y = np.array(values)

    model = LinearRegression()
    model.fit(X, y)

    slope = model.coef_[0]
    intercept = model.intercept_
    r_squared = model.score(X, y)

    if slope <= 0:
        return {
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_squared,
            "days_to_limit": None,
            "exhaustion_date": None,
            "message": "Metric is stable or declining. No exhaustion predicted."
        }

    days_to_limit = (limit - values[-1]) / slope
    exhaustion_date = dates[-1] + timedelta(days=int(days_to_limit))

    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": r_squared,
        "days_to_limit": int(days_to_limit),
        "exhaustion_date": exhaustion_date,
        "message": f"Metric will reach {limit}% in {int(days_to_limit)} days ({exhaustion_date.strftime('%Y-%m-%d')})"
    }
```

---

## Interpreting R² (Goodness of Fit)

| R² Value | Interpretation | Action |
|---|---|---|
| 0.90–1.00 | Strong linear trend | Trust the forecast |
| 0.70–0.89 | Moderate trend with noise | Use with caution, widen the alert window |
| < 0.70 | Weak linear fit | Data may be seasonal or nonlinear; linear regression is insufficient |

Disk usage typically has R² > 0.90 because growth is steady. CPU is noisier (R² ~0.5–0.7) because it varies by workload. For CPU, consider ARIMA or moving averages instead.

---

## Moving Average (Alternative for Noisy Data)

When the data is too noisy for regression, a moving average smooths it:

```python
def moving_average(values, window=7):
    """7-day moving average."""
    return [
        np.mean(values[max(0, i-window+1):i+1])
        for i in range(len(values))
    ]
```

The lab script automatically applies both models and compares their fits.

---

## Validation Checklist

- [ ] Three CSV files generated with 30 days of data each.
- [ ] Linear regression fitted for disk, CPU, and memory.
- [ ] Predicted exhaustion date calculated for each metric.
- [ ] R² score reported to assess fit quality.
- [ ] Forecast plots saved to `output/` with color-coded zones.
- [ ] Moving average applied to the noisiest metric for comparison.
