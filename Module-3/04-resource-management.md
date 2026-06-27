# 04 — Resource Management & OOM Testing

AI and ML applications (like our assistant which loads PyTorch, runs embeddings, and operates local databases) can consume significant system resources. Without proper boundaries, a single run-away container can consume all CPU and memory on a VM, starving critical system processes or other apps.

Kubernetes provides **Resource Requests and Limits** to prevent this.

---

## Resource Requests vs Limits

When defining container specs, you can specify boundaries for **CPU** (measured in cores or millicores) and **Memory** (measured in bytes, mebibytes `Mi`, or gibibytes `Gi`):

```
       ┌────────────────────────────────────────────────────────┐
       │                     PHYSICAL NODE                      │
       │                                                        │
       │  ┌─────────────────┐                                   │
       │  │ Limit: 512Mi    │ ◄── Maximum container can reach   │
       │  │                 │                                   │
       │  │                 │                                   │
       │  ├─────────────────┤                                   │
       │  │ Request: 400Mi  │ ◄── Guaranteed capacity reserved   │
       │  │                 │     by scheduler                  │
       │  └─────────────────┘                                   │
       └────────────────────────────────────────────────────────┘
```

### 1. Resource Requests
- **What it is**: The minimum amount of resource (CPU/Memory) the container is guaranteed to receive.
- **Role**: The Kubernetes scheduler uses requests to decide **which node** to place a Pod on. If a node does not have enough unreserved capacity to satisfy a Pod's request, the Pod will remain in a `Pending` state.

### 2. Resource Limits
- **What it is**: The absolute maximum amount of resource the container is allowed to consume.
- **Role**: The container runtime enforces these limits:
  - **CPU Limit**: If a container exceeds its CPU limit, the CPU is **throttled** (slowed down). The container will not be killed, but performance will degrade.
  - **Memory Limit**: If a container exceeds its memory limit, the operating system kernel immediately terminates the process with an **Out of Memory (OOM) Kill**. The Pod status changes to `OOMKilled` (Exit Code `137`).

---

## Configuring Resource Limits

Let's modify `k8s/assistant-deployment.yaml` to configure requests and limits suitable for our PyTorch/Streamlit assistant:
- **CPU Request**: `250m` (0.25 core)
- **Memory Request**: `400Mi` (400 Mebibytes)
- **CPU Limit**: `500m` (0.5 core)
- **Memory Limit**: `512Mi` (512 Mebibytes)

Edit `k8s/assistant-deployment.yaml` on the master VM:

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
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: aiops-assistant-secret
              key: openai-api-key
        # Add the resources block below:
        resources:
          requests:
            memory: "400Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### Apply the Configuration

On the master VM:
```bash
kubectl apply -f /home/vagrant/k8s/assistant-deployment.yaml
```

Check the status of the rollout:
```bash
kubectl rollout status deployment/aiops-assistant-deployment
```

---

## Lab: Simulating an Out-of-Memory (OOM) Event

We have modified the Streamlit assistant UI to include a **"Resource Management Lab"** section in the sidebar. This section contains a button labeled **"Simulate Large Dataset Ingestion (OOM)"**. 

When clicked, the app runs a Python script that quickly allocates over 800MB of RAM in a loop. Since this exceeds the limit of `512Mi`, the kernel will terminate the container.

Let's execute the experiment and observe Kubernetes' response.

### Step 1: Watch the Pods Live

On the master VM, open a terminal window and run `kubectl get pods` with the watch (`-w`) flag:
```bash
kubectl get pods -w
```

### Step 2: Trigger the OOM Event

1. Open your browser and navigate to the application dashboard: **`http://aiops.local`** (or your NodePort URL).
2. Locate the **"Kubernetes Lab Experiments"** panel in the left sidebar.
3. Click the **"Simulate Large Dataset Ingestion (OOM)"** button.

### Step 3: Observe the Terminal Output

Within 2–5 seconds, the web application will display an "Application Connection Error" or connection timeout. Look at your terminal output:

```text
NAME                                          READY   STATUS      RESTARTS   AGE
aiops-assistant-deployment-5fc4f7bf84-ab12d   1/1     Running     0          5m
aiops-assistant-deployment-5fc4f7bf84-xy78c   1/1     Running     0          5m

# Event Triggered:
aiops-assistant-deployment-5fc4f7bf84-xy78c   0/1     OOMKilled   0          5m
aiops-assistant-deployment-5fc4f7bf84-xy78c   0/1     Error       0          5m
aiops-assistant-deployment-5fc4f7bf84-xy78c   1/1     Running     1          5m10s
```

Observe that the Pod immediately transitions to `OOMKilled` (or `Error`), terminates, and is **automatically restarted** by Kubernetes (RESTARTS count increments to `1`).

### Step 4: Describe the Pod Status

To investigate what happened, use `kubectl describe pod` on the restarted Pod:

```bash
kubectl describe pod aiops-assistant-deployment-5fc4f7bf84-xy78c
```

Locate the `Containers` section and check the `Last State` detail:

```text
Containers:
  assistant:
    Container ID:   containerd://e62b1b3d...
    Image:          module2-assistant:latest
    State:          Running
      Started:      Sat, 27 Jun 2026 14:15:20 +0000
    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
      Started:      Sat, 27 Jun 2026 14:10:00 +0000
      Finished:     Sat, 27 Jun 2026 14:15:18 +0000
    Ready:          True
    Restart Count:  1
```

### Exit Code 137 Explained
In Linux systems, an exit code of `137` indicates that a process was killed by a **SIGKILL** signal (signal `9`). 
- When an application exceeds the memory limits configured in Kubernetes, the host operating system's Out-Of-Memory Killer (OOM Killer) issues a `kill -9` (`SIGKILL`) to safeguard node stability.
- Exit code formula: `128 + Signal Number` (for `SIGKILL`, $128 + 9 = 137$).

---

## What's Next

You've successfully seen how K8s manages resource boundaries and handles container crashes. In the next lesson, we will put Kubernetes' **self-healing** capabilities to the test with hands-on Break/Fix activities!
