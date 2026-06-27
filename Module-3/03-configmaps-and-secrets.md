# 03 — Managing Configuration & Secrets

AI/ML and AIOps applications require runtime configurations (like database connection strings, model names) and sensitive credentials (like the OpenAI API key). Hardcoding credentials inside container images is a major security vulnerability. 

Kubernetes provides two core resources to handle runtime configurations: **ConfigMaps** and **Secrets**.

---

## ConfigMaps vs Secrets

| Feature | ConfigMaps | Secrets |
|---|---|---|
| **Data Type** | Non-sensitive, plain text configuration. | Sensitive credentials, keys, certificates. |
| **Storage in K8s** | Stored in plain text in the K8s key-value store (`etcd`). | Stored as base64-encoded strings (obfuscated) in `etcd`. |
| **Common Use Cases** | Application port settings, DB hostname, model parameter configuration. | API keys, database passwords, SSL certificates, SSH keys. |

---

## How Kubernetes Secrets Work

Under the hood, Kubernetes Secrets store values in **Base64** format. 

> [!WARNING]
> **Base64 encoding is NOT encryption.** It is simply a way to represent binary data in text format. Anyone with read access to the namespace can decode a K8s secret easily by running `echo 'encoded-string' | base64 --decode`.
>
> In real production environments, Kubernetes is configured to **encrypt Secrets at rest** in `etcd`, and teams use external secret managers (such as HashiCorp Vault, AWS Secrets Manager, or Sealed Secrets) to inject credentials dynamically. We will explore these in the bonus lecture.

---

## Creating the Kubernetes Secret

To deploy the AIOps assistant, we need to store our OpenAI API Key in a Secret.

### Step 1: Base64 Encode Your API Key

On your host machine or the master VM, run the following command to encode your actual OpenAI API Key:

```bash
# Replace sk-proj-123456789... with your actual OpenAI API key
echo -n "sk-proj-123456789..." | base64
```

Example Output:
```text
c2stcHJvai0xMjM0NTY3ODkuLi4=
```
*(Make sure to use the `-n` flag with `echo` to avoid encoding a trailing newline character).*

### Step 2: Write the Secret Manifest

Create a file named `k8s/assistant-secret.yaml` on the master VM and paste the base64-encoded string:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aiops-assistant-secret
type: Opaque
data:
  # Paste your base64 encoded API key below
  openai-api-key: c2stcHJvai0xMjM0NTY3ODkuLi4=
```

### Apply the Secret

On the master VM:
```bash
kubectl apply -f /home/vagrant/k8s/assistant-secret.yaml
```

Output:
```
secret/aiops-assistant-secret created
```

Verify that the secret was created:
```bash
kubectl get secrets
```

---

## Injecting Secrets into the Deployment

Now that the Secret is created inside the cluster, we need to tell our Deployment to read the value from `aiops-assistant-secret` and expose it as the `OPENAI_API_KEY` environment variable inside the container.

Let's modify `k8s/assistant-deployment.yaml`. Open the deployment file on the master VM and update the container section:

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
        # Add the env block below:
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: aiops-assistant-secret
              key: openai-api-key
```

### Manifest Explanation

- **`env`**: Defines a list of environment variables to set in the container.
- **`name: OPENAI_API_KEY`**: The name of the environment variable that the python code (`llm_engine.py`) reads.
- **`valueFrom.secretKeyRef`**: Tells Kubernetes to load this value from a Secret.
  - **`name: aiops-assistant-secret`**: The name of the Secret object we created.
  - **`key: openai-api-key`**: The specific key in the secret data block we want to load.

---

## Applying the Updated Deployment

Apply the updated manifest on the master VM:

```bash
kubectl apply -f /home/vagrant/k8s/assistant-deployment.yaml
```

Output:
```
deployment.apps/aiops-assistant-deployment configured
```

Since the Deployment spec was updated, Kubernetes will perform a **rolling update**: it starts two new Pods with the updated environment configurations, waits for them to become healthy, and then terminates the two old Pods.

---

## Verifying the Secret Injection

Let's verify that the environment variable was injected correctly.

### Step 1: Find the running Pod names
```bash
kubectl get pods
```

### Step 2: Inspect environment variables inside a Pod
Run the `env` command inside one of the running pods using `kubectl exec`:

```bash
# Replace pod-name with your actual pod name (e.g. aiops-assistant-deployment-xxxxxx-xxxxx)
kubectl exec -it aiops-assistant-deployment-xxxxxx-xxxxx -- env | grep OPENAI_API_KEY
```

Expected Output:
```text
OPENAI_API_KEY=sk-proj-123456789...
```
*(Notice that Kubernetes automatically decodes the Base64 value and presents it as a plain-text API key inside the container environment!)*

### Step 3: Test the App

Open **`http://aiops.local`** in your host browser. Type an incident log (e.g. "API latency spiking on payment-gateway") and click **Analyze Incident**. The assistant should successfully retrieve historical context from ChromaDB, call the OpenAI API, and display the Root Cause Analysis report!

---

## What's Next

Now that our application is configured and running securely, let's explore **Resource Management**. AI workloads can be extremely CPU and memory-intensive. In the next lesson, we will set strict boundaries on our containers and observe what happens when they run out of memory.
