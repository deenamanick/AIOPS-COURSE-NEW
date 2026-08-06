# 06 — Production Patterns & Deliverables

Linear regression works well for steady growth, but production systems exhibit more complex behaviors: weekly traffic patterns, deployment spikes, seasonal business cycles. This lesson covers advanced forecasting patterns, governance, and your Module 9 deliverables.

---

## Advanced Forecasting Patterns

### SLO Breach Prediction

Instead of forecasting when a metric hits a fixed limit, forecast when the **error budget** will be exhausted:

```text
current_budget_remaining = 30%
budget_burn_rate = 2.5% per day
days_to_zero = 30 / 2.5 = 12 days
```

This directly answers: "At current trajectory, we breach the SLO in 12 days."

Combine this with the Module 7 error budget policy:

| Budget Remaining | Predicted to Exhaust In | Action |
|---|---|---|
| > 50% | > 30 days | Normal operations |
| 25–50% | 15–30 days | Review change failure rate |
| 10–25% | 5–15 days | Reduce deployment frequency |
| < 10% | < 5 days | Freeze deployments, fix reliability |

### Seasonal Decomposition

CPU and traffic often follow daily and weekly patterns:

```text
Monday 09:00 — peak traffic
Saturday 03:00 — minimum traffic
```

Linear regression would average these patterns out. For seasonal data, decompose the signal:

```text
observed = trend + seasonal + residual
```

Python's `statsmodels` library handles this:

```python
from statsmodels.tsa.seasonal import seasonal_decompose

result = seasonal_decompose(values, model='additive', period=24)
# result.trend     — the long-term direction
# result.seasonal  — the repeating daily pattern
# result.resid     — the unexplained noise
```

Forecast the **trend** component, then add the seasonal component back. This prevents false alerts during predictable traffic spikes.

### Anomaly Detection via Forecast

Once you have a forecast, any observation far from the prediction is an anomaly:

```python
def is_anomaly(actual, predicted, threshold_sigma=3):
    """Flag if actual deviates from predicted by more than 3 standard deviations."""
    residuals = [a - p for a, p in zip(actuals, predictions)]
    mean_residual = np.mean(residuals)
    std_residual = np.std(residuals)
    deviation = abs(actual - predicted)
    return deviation > (mean_residual + threshold_sigma * std_residual)
```

This is the foundation of forecast-based anomaly detection—a core AIOps capability.

---

## Governance and Operational Excellence

### Forecast Review Cadence

| Frequency | What to Review |
|---|---|
| Daily | Risk score dashboard, active predictive alerts |
| Weekly | DORA metrics trend, capacity forecasts |
| Monthly | Forecast accuracy review, weight tuning, model retraining |
| Quarterly | Capacity planning budget, infrastructure roadmap |

### Forecast Accuracy Tracking

Track how accurate your predictions were:

```python
def forecast_accuracy(predicted, actual):
    """Mean Absolute Percentage Error (MAPE)."""
    errors = [abs(p - a) / max(a, 0.001) for p, a in zip(predicted, actual)]
    return round(sum(errors) / len(errors) * 100, 1)
```

| MAPE | Quality |
|---|---|
| < 5% | Excellent |
| 5–15% | Good |
| 15–25% | Acceptable |
| > 25% | Retrain the model |

### Alert on the Forecaster

The forecasting system itself needs monitoring:

- Is the data pipeline producing fresh CSV/metrics?
- Has the model been retrained in the last 30 days?
- Is the MAPE increasing over time (model drift)?
- Are there gaps in the time-series data?

---

## Student Deliverables

### Deliverable 1: Forecasting Report

Submit the forecast outputs for disk, CPU, and memory:

- The three forecast plots (`output/*.png`)
- R² scores and predicted exhaustion dates
- Which metric had the strongest linear fit and why

### Deliverable 2: Risk Score Engine

Submit the risk engine output for three scenarios:

- Healthy system (Green)
- Disk pressure (Yellow)
- Cascading failure (Red)
- Include the breakdown table showing individual metric contributions

### Deliverable 3: DORA Dashboard

Submit the DORA metrics report:

- All four metric values and tier classifications
- The DORA dashboard plot
- One observation about what the metrics reveal about the team

### Deliverable 4: Predictive Alert Evidence

Submit the break/fix report:

- Prediction vs actual exhaustion time
- Prediction error percentage
- Screenshot or log of the alert firing before the failure
- One sentence: how much lead time did the predictive alert provide?

### Deliverable 5: Capacity Planning Recommendation

Write a one-page capacity plan:

- Current resource usage trends (from forecasts)
- Predicted exhaustion dates for each metric
- Risk score and severity
- Recommended actions and timeline
- Cost estimate (if applicable)

---

## Module Summary

You can now forecast resource exhaustion using linear regression, calculate composite risk scores, measure engineering performance with DORA metrics, and set predictive alerts that fire before failures happen. Combined with Module 7 (alerting) and Module 8 (correlation), you have a complete AIOps operations toolkit: **predict → prevent → detect → correlate → respond → recover**.

In Module 10, you will apply machine learning to detect anomalies automatically—moving beyond static thresholds and linear models to systems that learn what "normal" looks like.
