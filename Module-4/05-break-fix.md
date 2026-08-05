# 05 — Break/Fix Activities

In this lesson, you will act as an SRE and intentionally break things. You will push a broken test to observe how the CI pipeline blocks a bad deployment, then simulate an extreme traffic spike to stress-test the Horizontal Pod Autoscaler.

---

## Activity 1: Break the CI Pipeline with a Failing Test

The most powerful feature of a CI/CD pipeline is its ability to **block** bad code from reaching production. Let's demonstrate this.

### Step 1: Write a Broken Test

Create a new test file in your project: `tests/test_broken.py`:

```python
"""Intentionally broken test to demonstrate CI pipeline blocking."""


def test_always_fails():
    """This test will always fail, simulating a developer pushing broken code."""
    result = 2 + 2
    assert result == 5, f"Expected 5 but got {result} — this is intentionally broken!"
```

### Step 2: Commit and Push

```bash
git add tests/test_broken.py
git commit -m "feat: add new scoring logic (broken test)"
git push origin main
```

### Step 3: Observe the Pipeline Failure

Navigate to your GitHub repository → **Actions** tab. You will see the pipeline running:

```text
✅ Lint Code           — Passed
❌ Run Tests           — Failed
⬚ Build Docker Image  — Skipped (blocked by test failure)
⬚ Deploy to K8s       — Skipped (blocked by build failure)
```

Click on the failed **Run Tests** job to see the pytest output:

```text
tests/test_broken.py::test_always_fails FAILED

FAILED tests/test_broken.py::test_always_fails - AssertionError: Expected 5 but got 4
=================== 1 failed, 7 passed in 4.82s ===================
```

**Key Takeaway:** Because the `build` job has `needs: test`, the pipeline stopped immediately. No Docker image was built, no deployment was triggered. The broken code never reached production!

### Step 4: Fix the Test and Verify Green Pipeline

Delete the broken test:
```bash
rm tests/test_broken.py
git add -A
git commit -m "fix: remove broken test"
git push origin main
```

Watch the pipeline turn green:
```text
✅ Lint Code           — Passed
✅ Run Tests           — Passed
✅ Build Docker Image  — Passed
✅ Deploy to K8s       — Passed (waiting for approval if environment protection is enabled)
```

---

## Activity 2: Extreme Traffic Spike — Autoscaler Under Pressure

Let's push the HPA to its limits by generating significantly more traffic than the cluster can handle.

### Step 1: Confirm Current State

Check the current HPA and pod count:
```bash
kubectl get hpa
kubectl get pods
```

You should see 2 pods running with CPU well below 70%.

### Step 2: Generate Extreme Load

This time, send **10,000 requests** with **200 concurrent workers**:

```bash
hey -n 10000 -c 200 http://192.168.56.24:30501/
```

### Step 3: Watch the Autoscaler React

In a separate terminal, monitor the HPA and pods:
```bash
kubectl get hpa --watch
```

In another terminal:
```bash
watch kubectl get pods -o wide
```

You should observe the following progression:

1. **Phase 1 (0-30s):** CPU spikes past 70%. HPA calculates that it needs more replicas.
2. **Phase 2 (30-60s):** HPA scales from 2 → 3, then 3 → 4 pods. New pods enter `ContainerCreating` state.
3. **Phase 3 (60-120s):** HPA hits the maximum of 5 pods. Even at max capacity, CPU may remain above 70%.
4. **Phase 4 (After load stops):** CPU gradually drops. After the 5-minute cooldown, pods scale back down to 2.

### Step 4: Analyze the Results

After the load test completes, `hey` will print a summary:

```text
Summary:
  Total:        42.3156 secs
  Slowest:      8.2341 secs
  Fastest:      0.0312 secs
  Average:      0.8463 secs
  Requests/sec: 236.3200

Response time histogram:
  0.031 [1]     |
  0.851 [6842]  |■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
  1.671 [2156]  |■■■■■■■■■■■■■
  2.491 [701]   |■■■■
  3.311 [189]   |■
  ...

Status code distribution:
  [200] 9847 responses
  [502] 153 responses
```

**What to observe:**
- **502 errors:** Some requests failed because the pods couldn't keep up while new ones were spinning up. This is expected during aggressive scaling.
- **Slowest response time:** This tells you how long the worst-case user experience was during the spike.
- **Scale-up latency:** The time between the spike starting and the new pods becoming ready is your **autoscaler response time**.

---

## Activity 3: What Happens When HPA Hits the Maximum?

If the load exceeds what 5 pods can handle, HPA cannot scale further. This is called **headroom exhaustion**.

Signs of headroom exhaustion:
```bash
kubectl describe hpa aiops-assistant-deployment
```

Look for this warning:
```text
  Warning  FailedComputeMetricsReplicas  horizontalpodautoscaler  desired replica count limited by maximum replica count (5)
```

**What to do in production:**
1. **Increase `maxReplicas`** if your cluster has capacity.
2. **Add more nodes** to the cluster (Cluster Autoscaler).
3. **Optimize the application** to handle more requests per pod (caching, connection pooling).

---

## Summary of Troubleshooting Commands

| Command | What to Observe |
|---|---|
| `kubectl get hpa --watch` | Real-time HPA scaling decisions |
| `kubectl get pods --watch` | Pod creation and termination during scaling |
| `kubectl describe hpa <name>` | HPA events, warnings, and metric calculations |
| `kubectl top pods` | Live CPU/memory consumption per pod |
| `hey -n 10000 -c 200 <URL>` | Generate synthetic HTTP load for stress testing |

---

## What's Next

You've broken the pipeline, observed it block a bad deployment, and stress-tested the autoscaler to its limits. In the final lesson, we will look at **DORA metrics**, **deployment strategies** (blue-green, canary), and how elite SRE teams measure engineering velocity.
