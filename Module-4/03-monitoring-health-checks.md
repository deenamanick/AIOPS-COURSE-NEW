# 03 — Monitoring & Health Checks

Your CI pipeline is building and deploying the assistant, and your tests validate correctness before deployment. But what happens **after** the code reaches production? A container might start successfully but then hang, run out of memory, or lose connectivity to its database. Without monitoring, you won't know until users start complaining.

In this lesson, you will configure **Kubernetes health probes** to detect unhealthy containers and set up basic **resource visibility** so you can observe the state of your cluster.

---

## Why Monitoring Matters for AI Workloads

AI/ML workloads have unique failure modes that traditional web apps don't:

| Failure Mode | Example | Why It's Dangerous |
|---|---|---|
| **Silent Model Degradation** | The LLM starts returning low-quality responses due to a corrupted prompt template. | The app appears "up" but output quality drops — no crash, no error. |
| **Memory Creep** | ChromaDB's in-memory index grows slowly over hours until it triggers an OOM kill. | Pod restarts repeatedly with no obvious cause. |
| **GPU Deadlock** | A CUDA process hangs, consuming 100% GPU but producing zero output. | The pod reports `Running` but is completely stuck. |
| **Dependency Timeout** | The OpenAI API becomes unreachable or rate-limited. | Requests pile up, the app freezes, but the container is still alive. |

Kubernetes provides two probes to detect these issues automatically.

---

## Kubernetes Health Probes

### Liveness Probe
**Question it answers:** "Is the container still running, or is it stuck/deadlocked?"
- If the liveness probe fails, Kubernetes **kills and restarts** the container.
- Use this to recover from situations where the application is frozen.

### Readiness Probe
**Question it answers:** "Is the container ready to accept traffic?"
- If the readiness probe fails, Kubernetes **removes the Pod from the Service** (stops sending it traffic) but does NOT restart it.
- Use this for warm-up periods (e.g., loading ML models into memory).

```
  ┌───────────────────────────────────────────────────┐
  │                      POD                          │
  │                                                   │
  │   ┌──────────────┐    ┌──────────────┐            │
  │   │   Liveness   │    │  Readiness   │            │
  │   │    Probe     │    │    Probe     │            │
  │   └──────┬───────┘    └──────┬───────┘            │
  │          │                   │                    │
  │          │ Fails?            │ Fails?             │
  │          ▼                   ▼                    │
  │   Kill & Restart      Remove from Service         │
  │                       (stop routing traffic)      │
  └───────────────────────────────────────────────────┘
```

---

## Lab: Adding Health Probes to the Deployment

### Step 1: Update the Deployment Manifest

Open your `k8s/assistant-deployment.yaml` file (from Module 3) and add liveness and readiness probes to the container spec:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiops-assistant-deployment
  labels:
    app: aiops-assistant
spec:
  replicas: 2
  selector:
    matchLabels:
      app: aiops-assistant
  template:
    metadata:
      labels:
        app: aiops-assistant
    spec:
      containers:
      - name: assistant
        image: module2-assistant:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8501
        livenessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 30    # Wait 30s for the app to start before probing
          periodSeconds: 10          # Check every 10 seconds
          failureThreshold: 3        # Kill the container after 3 consecutive failures
        readinessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 10    # Start checking readiness after 10s
          periodSeconds: 5           # Check every 5 seconds
          failureThreshold: 3        # Remove from service after 3 failures
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Probe Configuration Explained

| Field | Liveness Value | Readiness Value | Purpose |
|---|---|---|---|
| `initialDelaySeconds` | 30 | 10 | How long to wait after container start before first probe. Liveness waits longer because we don't want to kill a container that's just slow to boot. |
| `periodSeconds` | 10 | 5 | How often to check. Readiness checks more frequently to quickly route traffic to healthy pods. |
| `failureThreshold` | 3 | 3 | Number of consecutive failures before taking action. |

### Step 2: Apply the Updated Deployment

On the master VM:
```bash
kubectl apply -f /home/vagrant/k8s/assistant-deployment.yaml
```

### Step 3: Verify Probes Are Active

Describe one of the pods to confirm the probes are configured:
```bash
kubectl describe pod -l app=aiops-assistant
```

Look for the `Liveness` and `Readiness` sections in the output:
```text
    Liveness:       http-get http://:8501/_stcore/health delay=30s timeout=1s period=10s #success=1 #failure=3
    Readiness:      http-get http://:8501/_stcore/health delay=10s timeout=1s period=5s #success=1 #failure=3
```

---

## Lab: Resource Visibility with kubectl top

To observe real-time CPU and memory consumption of your pods, you need the **Kubernetes Metrics Server**.

### Step 1: Install Metrics Server

On the master VM:
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

For local clusters (Vagrant/Kind), you may need to add the `--kubelet-insecure-tls` flag. Patch the metrics-server deployment:
```bash
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'
```

Wait 60 seconds for the metrics server to start collecting data.

### Step 2: View Node Resource Usage

```bash
kubectl top nodes
```

Expected Output:
```text
NAME      CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%
master    250m         12%    1200Mi          24%
worker1   180m         9%     890Mi           29%
worker2   150m         7%     750Mi           25%
```

### Step 3: View Pod Resource Usage

```bash
kubectl top pods
```

Expected Output:
```text
NAME                                          CPU(cores)   MEMORY(bytes)
aiops-assistant-deployment-5fc4f7bf84-ab12d   45m          180Mi
aiops-assistant-deployment-5fc4f7bf84-xy78c   38m          165Mi
```

This gives you real-time visibility into how much CPU and memory each pod is consuming — essential for capacity planning and detecting resource leaks.

---

## Summary of Monitoring Commands

| Command | What It Shows | When to Use |
|---|---|---|
| `kubectl top nodes` | CPU/Memory usage per node | Capacity planning, detecting overloaded nodes |
| `kubectl top pods` | CPU/Memory usage per pod | Detecting memory leaks, right-sizing resource requests |
| `kubectl describe pod <name>` | Probe status, events, restart count | Debugging why a pod is crashing or not receiving traffic |
| `kubectl get events --sort-by=.lastTimestamp` | Cluster-wide event stream | Identifying systemic issues (node pressure, scheduling failures) |

---

## What's Next

You now have health checks preventing broken pods from receiving traffic, and resource visibility to monitor consumption. But what happens when traffic spikes beyond what your 2 pods can handle? In the next lesson, we will configure **Horizontal Pod Autoscaling** to automatically scale your application based on CPU utilization.
