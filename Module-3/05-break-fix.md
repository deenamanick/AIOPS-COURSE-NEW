# 05 — Break/Fix Activities

In this lesson, we will perform three hands-on troubleshooting and resilience testing exercises. You will act as an SRE and observe Kubernetes' automatic response mechanisms, scale resources, and debug container image errors.

---

## Activity 1: Pod Deletion & Self-Healing

One of Kubernetes' primary value propositions is **self-healing**. If a container or node fails in production, Kubernetes will automatically recreate it to match the desired state defined in your Deployment.

Let's test this behavior.

### Step 1: Check Current Running Pods

On the master VM, list your current running Pods:
```bash
kubectl get pods
```

Example Output:
```text
NAME                                          READY   STATUS    RESTARTS   AGE
aiops-assistant-deployment-5fc4f7bf84-ab12d   1/1     Running   1          10m
aiops-assistant-deployment-5fc4f7bf84-xy78c   1/1     Running   0          10m
```

### Step 2: Delete a Running Pod

Simulate a server crash by deleting one of the running pods manually:
```bash
# Replace pod-name with one of the Pod names from your output
kubectl delete pod aiops-assistant-deployment-5fc4f7bf84-ab12d
```

### Step 3: Watch K8s Self-Heal

Immediately run the list pods command:
```bash
kubectl get pods
```

Expected Output:
```text
NAME                                          READY   STATUS        RESTARTS   AGE
aiops-assistant-deployment-5fc4f7bf84-ab12d   1/1     Terminating   1          11m
aiops-assistant-deployment-5fc4f7bf84-gh89k   1/1     Running       0          3s
aiops-assistant-deployment-5fc4f7bf84-xy78c   1/1     Running       0          11m
```

Observe that while the deleted pod is in the `Terminating` state, the ReplicaSet has already created a brand new Pod (`gh89k`) which is in the `Running` state! Kubernetes guarantees that the running system always conforms to your declared desired state.

---

## Activity 2: Scaling Replicas

Operations workloads experience varying traffic levels. SREs must be able to scale application capacity up or down dynamically.

### Step 1: Scale Replicas to 0

Suppose we need to temporarily stop all instances of our application (e.g. for maintenance or to cut costs). Scale the deployment replicas to `0`:

```bash
kubectl scale deployment/aiops-assistant-deployment --replicas=0
```

Verify that all pods are terminating:
```bash
kubectl get pods
```
*(After a few seconds, the output should read: "No resources found in default namespace.")*

### Step 2: Scale Replicas to 3

Traffic is spiking! Scale the deployment up to `3` replicas:

```bash
kubectl scale deployment/aiops-assistant-deployment --replicas=3
```

Check the pod status:
```bash
kubectl get pods -o wide
```

Expected Output:
```text
NAME                                          READY   STATUS    RESTARTS   AGE    NODE
aiops-assistant-deployment-5fc4f7bf84-gh89k   1/1     Running   0          2m     worker1
aiops-assistant-deployment-5fc4f7bf84-xy78c   1/1     Running   0          2m     worker2
aiops-assistant-deployment-5fc4f7bf84-jk23w   1/1     Running   0          10s    worker1
```

Kubernetes spun up 3 Pods, spreading them across the worker nodes automatically.

---

## Activity 3: Debugging Wrong Image Tags

A common deployment error occurs when a developer specifies an incorrect container image tag in the deployment manifest. Kubernetes will fail to fetch the image, placing the pod in an error state.

### Step 1: Inject the Failure

Open your `k8s/assistant-deployment.yaml` file on the master VM and edit the container image name to use an invalid tag:

```yaml
# Inside k8s/assistant-deployment.yaml:
      containers:
      - name: assistant
        image: module2-assistant:wrongtag  # Injected incorrect tag
```

Apply the broken configuration:
```bash
kubectl apply -f /home/vagrant/k8s/assistant-deployment.yaml
```

### Step 2: Observe the Pod Error

Check the status of the Pods:
```bash
kubectl get pods
```

Expected Output:
```text
NAME                                          READY   STATUS             RESTARTS   AGE
aiops-assistant-deployment-64d84f8dbd-mn12k   0/1     ImagePullBackOff   0          12s
aiops-assistant-deployment-64d84f8dbd-pq34l   0/1     ErrImagePull       0          12s
```
The new Pods are stuck in `ErrImagePull` or `ImagePullBackOff`.

### Step 3: SRE Troubleshooting Workflow

To debug why the Pods are failing to start:

#### 1. Try checking container logs
```bash
kubectl logs aiops-assistant-deployment-64d84f8dbd-mn12k
```
Output:
```text
Error from server (BadRequest): container "assistant" in pod "aiops-assistant-deployment-64d84f8dbd-mn12k" is waiting to start: trying and failing to pull image
```
*Takeaway:* If a container fails to pull, the application inside it never runs. Therefore, `kubectl logs` will not show any application logs. We must look at **Kubernetes event logs** instead.

#### 2. Describe the Pod to check event logs
```bash
kubectl describe pod aiops-assistant-deployment-64d84f8dbd-mn12k
```

Scroll to the bottom of the output and look at the **Events** timeline:

```text
Events:
  Type     Reason     Age                From               Message
  ----     ------     ----               ----               -------
  Normal   Scheduled  45s                default-scheduler  Successfully assigned default/aiops-assistant-deployment-64d84f8dbd-mn12k to worker1
  Normal   BackOff    10s (x3 over 35s)  kubelet            Back-off pulling image "module2-assistant:wrongtag"
  Warning  Failed     10s (x3 over 35s)  kubelet            Error: ImagePullBackOff
  Warning  Failed     5s (x4 over 40s)   kubelet            Failed to pull image "module2-assistant:wrongtag": failed to resolve reference "docker.io/library/module2-assistant:wrongtag": not found
```

*Takeaway:* The warning tells us exactly what went wrong. The kubelet on `worker1` tried to fetch `module2-assistant:wrongtag` but returned a reference `not found` error.

### Step 4: Remediate the Deployment

1. Restore the correct tag (`latest` or `your_username/aiops-assistant:v1`) in `k8s/assistant-deployment.yaml`.
2. Apply the configuration again:
   ```bash
   kubectl apply -f /home/vagrant/k8s/assistant-deployment.yaml
   ```
3. Watch the deployment recover:
   ```bash
   kubectl get pods
   ```

---

## Summary of Troubleshooting CLI Commands

| Command | Action | When to Use |
|---|---|---|
| `kubectl get pods` | Lists Pod status | Check high-level health of your containers. |
| `kubectl describe pod <name>` | Shows detailed spec + events | Debug startup issues, node assignment, pull errors, and resource issues. |
| `kubectl logs <name>` | Prints container stdout | Debug application logic errors, tracebacks, database connection issues. |
| `kubectl get events` | Prints cluster event stream | Identify node bottlenecks, networking issues, or container restarts cluster-wide. |
