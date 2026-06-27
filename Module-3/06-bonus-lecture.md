# 06 — Production AI Workloads & Deliverables

Congratulations on completing the core lab components of Module 3! Before you submit your deliverables, let's look at how large-scale enterprise SRE teams orchestrate production AI/ML workloads on Kubernetes.

---

## 1. GPU Scheduling in Kubernetes

The AIOps assistant we built runs a small sentence-transformer model that easily runs on a CPU. However, large language models (LLMs) and deep learning training pipelines require significant compute power, which requires **Graphics Processing Units (GPUs)**.

By default, Kubernetes scheduler only knows about CPU and memory. To enable GPU scheduling:
1. **Device Plugins**: You install a vendor-specific device plugin, such as the **NVIDIA Device Plugin for Kubernetes**, as a DaemonSet.
2. **Resource Requests**: Once installed, GPUs are exposed as schedulable resources. You request them in your container spec just like CPU or memory:

```yaml
resources:
  limits:
    nvidia.com/gpu: 1  # Requests 1 physical NVIDIA GPU for this container
```

---

## 2. Stateful AI: Persistent Volumes (PV)

Our local ChromaDB setup uses an in-memory database configuration (`EphemeralClient()`). If our application Pod crashes or restarts, all ingested incident vector databases are lost, and the application must re-embed the data.

For production, you need persistent storage. Kubernetes achieves this via **StatefulSets** and **Persistent Volumes**:

```
      ┌────────────────────────────────────────────────────────┐
      │                     POD RE-SCHEDULE                    │
      │                                                        │
      │   ┌───────────────┐               ┌───────────────┐    │
      │   │    Old Pod    │               │    New Pod    │    │
      │   │  (Terminated) │               │   (Started)   │    │
      │   └───────┬───────┘               └───────┬───────┘    │
      └───────────┼───────────────────────────────┼────────────┘
                  │                               │
                  │   ┌──────────────────────┐    │ (Auto re-attaches)
                  └──►│ PersistentVol. Claim │◄───┘
                      └──────────┬───────────┘
                                 ▼
                      ┌──────────────────────┐
                      │  Persistent Volume   │
                      │  (ChromaDB Storage)  │
                      └──────────────────────┘
```

- **Persistent Volume (PV)**: A piece of storage in the cluster (e.g. AWS EBS, GCP Persistent Disk, NFS) provisioned by an administrator.
- **Persistent Volume Claim (PVC)**: A request for storage by a developer.
- When a pod restarts, Kubernetes detaches the storage volume from the old pod and attaches it to the new pod, ensuring no vector data is lost.

---

## 3. Production Secret Management

In Lesson 3, we wrote a base64 encoded string into a raw YAML file. If this YAML file is committed to a public Git repository, your OpenAI API key is leaked.

For production environments, SREs use:
1. **Sealed Secrets (Bitnami)**: Allows you to encrypt your secrets using asymmetric cryptography. You can safely commit `SealedSecret` YAML files to Git because only the controller running inside your cluster has the private key to decrypt them.
2. **External Secrets Operator (ESO)**: Integrates Kubernetes directly with cloud providers' secret managers (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault). The secrets are stored securely outside Kubernetes and automatically synced into native K8s Secrets at runtime.
3. **Secret Injection (Vault Agent)**: Inserts secrets directly into the container memory filesystem (RAM disk) without ever writing them to K8s resource storage.

---

## Student Deliverables

To complete this module, you must submit the following deliverables to your instructor.

### Deliverable 1: Kubernetes Manifests
Submit your complete, syntactically correct Kubernetes YAML manifests:
- `assistant-deployment.yaml`
- `assistant-service.yaml`
- `assistant-ingress.yaml`
- `assistant-secret.yaml` (with the base64 API key redacted: `openai-api-key: <REDACTED>`)

### Deliverable 2: Application Running on Ingress Host
Provide a screenshot showing your web browser accessing the AIOps assistant interface via the custom domain host name:
- URL visible in browser address bar: **`http://aiops.local`**
- An analysis output showing a successful LLM-generated RCA.

### Deliverable 3: Out-of-Memory (OOM) Termination Logs
Provide a copy-paste of the output of your `kubectl describe pod` command showing that your pod was terminated due to an OOM event:
- Look for: `Reason: OOMKilled`, `Exit Code: 137`, and `Restart Count: 1`.

### Deliverable 4: SRE Reflections (Written Answers)
Answer the following two scenarios (2-3 sentences each):
1. **Scenario A**: Your deployment replicas are set to `2`. One of your worker nodes runs out of power and goes offline. What will Kubernetes do, and how does this affect application availability?
2. **Scenario B**: You set your application memory request to `1Gi` and limit to `2Gi`. The worker nodes in your cluster only have `512Mi` of free memory available. What will happen to your Pods when you run `kubectl apply`?
