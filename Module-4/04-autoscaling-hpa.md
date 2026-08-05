# 04 — Autoscaling with HPA

Your application has health probes, monitoring, and resource visibility. But with only 2 replicas, what happens during a traffic spike? If both pods saturate their CPU at 100%, requests start queuing, latency skyrockets, and users experience timeouts. You need Kubernetes to **automatically** add more pods when demand increases and remove them when it subsides.

This is the role of the **Horizontal Pod Autoscaler (HPA)**.

---

## What is HPA?

The Horizontal Pod Autoscaler is a Kubernetes controller that automatically scales the number of pod replicas in a Deployment based on observed metrics (CPU utilization, memory usage, or custom metrics).

```
  ┌────────────────────────────────────────────────────────────────┐
  │                  Horizontal Pod Autoscaler                     │
  │                                                                │
  │   Target CPU: 70%    Min Replicas: 2    Max Replicas: 5        │
  │                                                                │
  │   Current CPU: 85% ──► SCALE UP ──► Add 1 Pod                 │
  │   Current CPU: 30% ──► SCALE DOWN ──► Remove 1 Pod            │
  │   Current CPU: 65% ──► NO ACTION ──► Stay at current count    │
  └────────────────────────────────────────────────────────────────┘
```

### How HPA Makes Decisions

HPA continuously monitors the average CPU (or memory) across all pods in a deployment. It uses this formula to calculate the desired number of replicas:

```
desiredReplicas = ceil( currentReplicas × (currentMetricValue / targetMetricValue) )
```

**Example:**
- You have **2 pods** and the target CPU is **70%**.
- Current average CPU across pods is **85%**.
- `desiredReplicas = ceil(2 × (85 / 70)) = ceil(2.43) = 3`
- HPA adds 1 more pod.

---

## Prerequisites: Metrics Server

HPA requires the **Kubernetes Metrics Server** to read real-time CPU/memory data from pods. If you installed it in the previous lesson, verify it's running:

```bash
kubectl get deployment metrics-server -n kube-system
```

Expected output:
```text
NAME             READY   UP-TO-DATE   AVAILABLE   AGE
metrics-server   1/1     1            1           5m
```

If it's not installed, refer to Lesson 03 for installation instructions.

---

## Lab: Configuring HPA

### Step 1: Verify Resource Requests Are Set

HPA requires `resources.requests.cpu` to be defined in the Deployment manifest. If you updated the deployment in Lesson 03, you should already have this:

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"      # ← HPA needs this to calculate percentage
  limits:
    memory: "512Mi"
    cpu: "500m"
```

If your deployment doesn't have resource requests, HPA will fail with the error: `"missing request for cpu"`.

### Step 2: Create the HPA

You can create an HPA using a single `kubectl` command:

```bash
kubectl autoscale deployment aiops-assistant-deployment \
  --cpu-percent=70 \
  --min=2 \
  --max=5
```

This tells Kubernetes:
- **Target CPU**: Scale when average CPU across pods exceeds **70%**.
- **Min replicas**: Never scale below **2** pods (ensuring high availability).
- **Max replicas**: Never scale above **5** pods (preventing runaway costs).

### Step 3: Verify the HPA

```bash
kubectl get hpa
```

Expected Output:
```text
NAME                         REFERENCE                               TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
aiops-assistant-deployment   Deployment/aiops-assistant-deployment   35%/70%   2         5         2          30s
```

The `TARGETS` column shows `35%/70%` — meaning current average CPU is 35% and the target threshold is 70%. Since 35% < 70%, HPA keeps the replica count at the minimum (2).

### Alternative: HPA as a YAML Manifest

You can also define the HPA as a declarative manifest. Create `k8s/assistant-hpa.yaml`:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aiops-assistant-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aiops-assistant-deployment
  minReplicas: 2
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

Apply it:
```bash
kubectl apply -f /home/vagrant/k8s/assistant-hpa.yaml
```

---

## Lab: Generating Synthetic Load

Now let's force the autoscaler to react! We will use `hey`, a lightweight HTTP load generator, to flood our assistant with requests.

### Step 1: Install `hey` on Your Host Machine

```bash
# Linux
wget https://hey-release.s3.us-east-2.amazonaws.com/hey_linux_amd64 -O hey
chmod +x hey
sudo mv hey /usr/local/bin/

# macOS
brew install hey
```

### Step 2: Blast the Application

Send 2000 requests with 50 concurrent workers to the NodePort service:

```bash
hey -n 2000 -c 50 http://192.168.56.24:30501/
```

### Step 3: Watch HPA React in Real Time

Open a second terminal and watch the HPA status continuously:

```bash
kubectl get hpa --watch
```

Expected progression:
```text
NAME                         TARGETS    MINPODS   MAXPODS   REPLICAS   AGE
aiops-assistant-deployment   35%/70%    2         5         2          2m
aiops-assistant-deployment   82%/70%    2         5         2          2m30s
aiops-assistant-deployment   82%/70%    2         5         3          3m
aiops-assistant-deployment   91%/70%    2         5         3          3m30s
aiops-assistant-deployment   91%/70%    2         5         4          4m
```

Watch the pods scale up:
```bash
kubectl get pods -o wide
```

You should see **3, 4, or even 5 pods** spinning up as Kubernetes reacts to the CPU pressure!

### Step 4: Watch HPA Scale Down

After the `hey` load test finishes, the CPU will drop back below 70%. HPA has a **cooldown period** (default 5 minutes for scale-down) to prevent flapping. After the cooldown, pods will gradually be terminated:

```text
aiops-assistant-deployment   25%/70%    2         5         4          9m
aiops-assistant-deployment   18%/70%    2         5         3          11m
aiops-assistant-deployment   12%/70%    2         5         2          14m
```

---

## HPA Behavior Configuration

| Parameter | Default | Description |
|---|---|---|
| Scale-up stabilization window | 0s | HPA scales up immediately when threshold is breached. |
| Scale-down stabilization window | 300s (5 min) | HPA waits 5 minutes before scaling down to avoid flapping. |
| Tolerance | 10% | HPA won't act unless the metric deviates by more than 10% from the target. |

---

## What's Next

You've seen autoscaling in action! But what happens when a broken test is pushed to your pipeline? In the next lesson, we will perform **Break/Fix Activities** — intentionally breaking the CI pipeline and observing the autoscaler under extreme conditions.
