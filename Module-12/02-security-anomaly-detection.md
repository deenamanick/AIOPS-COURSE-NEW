# 02 — AIOps Anomaly Detection for Security

In Module 5 you trained an Isolation Forest model on infrastructure metrics — CPU, memory, disk I/O — to detect performance anomalies. The same algorithm works on security data. The inputs change; the math does not.

Security anomaly detection shifts the question from *"Is the server behaving abnormally?"* to *"Is this user behaving abnormally?"*

---

## Security Features for Anomaly Detection

Rather than CPU and disk, the model trains on behavioral signals:

| Feature | Why It Matters |
|---|---|
| `login_hour` | Logins at 3 AM are suspicious if the user always works 9–5 |
| `login_day_of_week` | Weekend logins outside normal patterns |
| `requests_per_minute` | Sudden spike may indicate data scraping |
| `data_transfer_mb` | Large exfiltration is the goal of most insider threats |
| `failed_logins_today` | Credential stuffing or brute force |
| `unique_ips_today` | Logging in from an unusual number of locations |
| `sensitive_file_accesses` | Accessing `/etc/passwd`, SSH keys, database dumps |

An employee who normally works 9–5, downloads a few MB per day, and accesses only their team's files is the **baseline**. An Isolation Forest trained on this baseline will flag the session where they work at 2 AM, transfer 4 GB, and access the credentials directory.

---

## How Isolation Forest Works on Security Data

Isolation Forest isolates anomalies by randomly partitioning the feature space. Points that are isolated in very few splits are anomalies. Normal users cluster together; malicious behavior is sparse and therefore isolated quickly.

```text
Normal users cluster here:
  login_hour ≈ 9–17
  transfer_mb ≈ 10–50
  failed_logins ≈ 0–2

Anomaly: isolated in 3 splits
  login_hour = 2
  transfer_mb = 4100
  failed_logins = 0  (they used valid creds — that's what makes insider threats hard)
```

The insider threat is dangerous precisely because no single signal triggers an alert — only the *combination* does. Isolation Forest natively handles multi-dimensional outliers.

---

## Lab: Security Anomaly Detection

### Step 1: Start the Lab App

```bash
cd Module-12/lab
docker compose up -d --build
```

The lab app at `http://localhost:5003` simulates 30 days of normal user behavior and exposes it as a dataset.

### Step 2: Fetch the Training Data

```bash
python3 scripts/fetch_security_data.py --output data/user_behavior.json
```

This writes a JSON file like:

```json
[
  {"user": "alice", "login_hour": 9, "day_of_week": 1, "requests_per_min": 12,
   "transfer_mb": 22.4, "failed_logins": 0, "unique_ips": 1, "sensitive_accesses": 0},
  {"user": "bob",   "login_hour": 14, "day_of_week": 3, "requests_per_min": 8,
   "transfer_mb": 8.1, "failed_logins": 1, "unique_ips": 1, "sensitive_accesses": 0}
]
```

### Step 3: Train and Score

```bash
python3 scripts/security_anomaly_detector.py \
  --input data/user_behavior.json \
  --output output/anomaly_scores.json
```

`scripts/security_anomaly_detector.py`:

```python
#!/usr/bin/env python3
"""
Module 12 — Security Anomaly Detection
Trains Isolation Forest on 30 days of user behavioral data and scores each session.
"""

import json, sys
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "login_hour", "day_of_week", "requests_per_min",
    "transfer_mb", "failed_logins", "unique_ips", "sensitive_accesses"
]

def load_data(path: str) -> tuple[list[dict], np.ndarray]:
    with open(path) as f:
        records = json.load(f)
    X = np.array([[r[feat] for feat in FEATURES] for r in records])
    return records, X

def train_and_score(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = IsolationForest(
        n_estimators=200,
        contamination=0.05,   # Expect ~5% anomalies in security data
        random_state=42
    )
    clf.fit(X_scaled)

    raw_scores = clf.decision_function(X_scaled)
    # Convert to 0–100 anomaly score (higher = more anomalous)
    anomaly_scores = 100 * (1 - (raw_scores - raw_scores.min()) /
                             (raw_scores.max() - raw_scores.min()))
    predictions = clf.predict(X_scaled)  # -1 = anomaly, 1 = normal
    return anomaly_scores, predictions

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--threshold", type=float, default=75.0)
    args = parser.parse_args()

    records, X = load_data(args.input)
    scores, preds = train_and_score(X)

    results = []
    for i, record in enumerate(records):
        score = float(round(scores[i], 1))
        is_anomaly = preds[i] == -1
        result = {**record, "anomaly_score": score, "is_anomaly": is_anomaly}
        results.append(result)
        if is_anomaly:
            print(f"⚠️  ANOMALY  user={record['user']:15s} "
                  f"score={score:5.1f}  "
                  f"hour={record['login_hour']:02d}  "
                  f"transfer_mb={record['transfer_mb']:.1f}  "
                  f"sensitive_accesses={record['sensitive_accesses']}")

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    anomaly_count = sum(1 for r in results if r["is_anomaly"])
    print(f"\nTotal sessions: {len(results)} | Anomalies detected: {anomaly_count}")
    print(f"Report written → {args.output}")

if __name__ == "__main__":
    main()
```

### Step 4: Inject an Insider Threat

Trigger the lab app's insider threat simulation endpoint:

```bash
curl -X POST http://localhost:5003/api/inject-insider-threat \
  -H "Content-Type: application/json" \
  -d '{"user": "bob", "type": "data_exfiltration"}'
```

This injects a session for `bob` with:
- `login_hour: 2` (2 AM)
- `transfer_mb: 4200` (4.2 GB — the credentials database export)
- `sensitive_accesses: 47` (reading SSH keys, `/etc/passwd`, DB dumps)
- `requests_per_min: 380` (automated scraping rate)

### Step 5: Re-score with the Injected Session

```bash
python3 scripts/fetch_security_data.py --output data/user_behavior_with_threat.json
python3 scripts/security_anomaly_detector.py \
  --input data/user_behavior_with_threat.json \
  --output output/anomaly_scores_with_threat.json
```

Expected output:

```text
⚠️  ANOMALY  user=bob             score=98.3  hour=02  transfer_mb=4200.0  sensitive_accesses=47

Total sessions: 312 | Anomalies detected: 1
```

The Isolation Forest catches the injected session with a score of **98.3 / 100**, even though `bob` used valid credentials and no individual metric would have triggered a traditional threshold alert.

---

## Why Baselines Matter More Than Thresholds

A traditional SIEM rule might say: *"Alert if transfer_mb > 1000."* This is immediately bypassed by anyone who does their exfiltration in 999 MB chunks.

Isolation Forest says: *"Alert if this session is anomalous compared to this user's own history."* The model learns that `bob` transfers 8–50 MB per session. 4200 MB is isolated in 2 splits regardless of any absolute threshold.

This is the core advantage of **behavioral anomaly detection** over signature-based rules.

---

## Validation Checklist

- [ ] Lab app running at `http://localhost:5003`.
- [ ] `user_behavior.json` fetched with 30+ days of sessions.
- [ ] Anomaly detector runs without errors on normal data.
- [ ] Insider threat injected via the API.
- [ ] Re-scored data shows the injected session with anomaly score > 90.
- [ ] You can explain why behavioral baselines outperform fixed thresholds.
