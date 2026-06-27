# 02 — Services & Ingress

Now that your Pods are running, you need a reliable way to access them. In Kubernetes, Pods are ephemeral; if a Pod is rescheduled, its IP address changes. We need a stable abstraction that sits in front of our Pods and load balances traffic to them. This is the role of a **Service**.

To route web traffic from outside the cluster based on domain names and paths, we use an **Ingress**.

---

## Kubernetes Service Types

Kubernetes offers different Service types depending on how you want to expose your pods:

| Service Type | Scope | How It Works | Common Use Case |
|---|---|---|---|
| **ClusterIP** | Internal Only | Assigns a stable IP address accessible *only* within the cluster. | Inter-service communication (e.g., App talking to Database). |
| **NodePort** | External | Exposes the service on a static port (in the `30000–32767` range) on *every* Node IP. | Basic external access, testing, local labs. |
| **LoadBalancer** | External | Provisions a cloud provider's load balancer (AWS NLB/ALB, GCP LB) that routes to your Service. | Production apps running in cloud environments (EKS, GKE, AKS). |
| **ExternalName** | External | Maps a service to a DNS name (using a CNAME record). | Mapping K8s services to external databases or APIs. |

---

## Creating the NodePort Service

Let's write a manifest to expose the Streamlit assistant using a `NodePort` service. This will open a port on our Vagrant VM nodes that we can access directly from our host machine.

Create a file named `k8s/assistant-service.yaml` on the master node:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: aiops-assistant-service
spec:
  type: NodePort
  selector:
    app: aiops-assistant
  ports:
  - port: 8501         # The port exposed inside the cluster
    targetPort: 8501   # The port the Streamlit app is listening on in the container
    nodePort: 30501    # The static port opened on every Kubernetes VM node
```

### Port Definitions Explained

- **`port` (8501)**: The internal port other services inside the cluster will use to communicate with this service.
- **`targetPort` (8501)**: The port on the container where the network traffic is directed. Streamlit runs on `8501`.
- **`nodePort` (30501)**: The port exposed to the outside world. This must be between `30000` and `32767`. If left empty, Kubernetes will assign a random port.

### Apply the Service

On the master VM:
```bash
kubectl apply -f /home/vagrant/k8s/assistant-service.yaml
```

Output:
```
service/aiops-assistant-service created
```

Check service status:
```bash
kubectl get services
```

Expected output:
```
NAME                      TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
kubernetes                ClusterIP   10.96.0.1       <none>        443/TCP          15m
aiops-assistant-service   NodePort    10.103.88.199   <none>        8501:30501/TCP   30s
```

### Accessing the App via NodePort

Since the service exposes port `30501` on every node, you can now access the Streamlit UI from your host machine's browser using any of the node IPs:
- Master: `http://192.168.56.24:30501`
- Worker 1: `http://192.168.56.25:30501`
- Worker 2: `http://192.168.56.26:30501`

Try opening `http://192.168.56.24:30501` in your host browser to confirm it works!

---

## Routing Traffic with Nginx Ingress

While NodePort works fine for local testing, exposing application ports directly is not practical for production. If you had 50 applications, you would have to manage 50 different ports.

Instead, we use an **Ingress Controller** (like **Nginx Ingress**). An Ingress Controller acts as an reverse-proxy entrypoint to the cluster, listening on standard HTTP/HTTPS ports (80/443) and routing traffic to internal services based on domain names or URL paths.

```
Request: http://aiops.local/
            │
            ▼
┌───────────────────────┐
│   Ingress Controller  │ (Nginx reverse-proxy on Port 80)
└───────────┬───────────┘
            │ (Matches host: aiops.local)
            ▼
┌───────────────────────┐
│   K8s Service         │ (aiops-assistant-service)
└───────────┬───────────┘
            ├─────────────────────────┐
            ▼                         ▼
 ┌─────────────────────┐   ┌─────────────────────┐
 │ Pod 1 (Streamlit)   │   │ Pod 2 (Streamlit)   │
 └─────────────────────┘   └─────────────────────┘
```

### Step 1: Install Nginx Ingress Controller

For our bare-metal kubeadm Vagrant cluster, we deploy the official Nginx Ingress controller using a manifest pre-configured for bare-metal providers:

On the master VM, run:
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.1/deploy/static/provider/baremetal/deploy.yaml
```

Wait a minute for the ingress controller pods to become healthy:
```bash
kubectl get pods -n ingress-nginx
```

Ensure the pod prefixed with `ingress-nginx-controller` is in the `Running` state.

*(Note: If you are using Minikube, run `minikube addons enable ingress` instead).*

### Step 2: Create the Ingress Manifest

Create a file named `k8s/assistant-ingress.yaml` on the master node:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: aiops-assistant-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
spec:
  rules:
  - host: aiops.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: aiops-assistant-service
            port:
              number: 8501
```

### Manifest Explanation

- **`annotations.kubernetes.io/ingress.class: "nginx"`**: Tells Kubernetes to configure the Nginx Ingress Controller to manage this routing rule.
- **`host: aiops.local`**: The domain name this rule applies to.
- **`path: /`**: Routes all paths (e.g. `/`, `/analytics`, `/search`) to the specified service.
- **`service.name: aiops-assistant-service`**: Directs matching traffic to our service.
- **`service.port.number: 8501`**: Maps to port 8501 (which is the targetPort of our service).

### Apply the Ingress

On the master VM:
```bash
kubectl apply -f /home/vagrant/k8s/assistant-ingress.yaml
```

Check the status:
```bash
kubectl get ingress
```

Expected output:
```
NAME                      CLASS    HOSTS         ADDRESS   PORTS   AGE
aiops-assistant-ingress   <none>   aiops.local             80      10s
```

### Step 3: Configure Host DNS

Because `aiops.local` is a custom local hostname, your web browser doesn't know how to resolve it. You must map it in your host operating system's `hosts` file.

On your **host machine** (not inside the VM), open `/etc/hosts` (Linux/macOS) or `C:\Windows\System32\drivers\etc\hosts` (Windows) as Administrator and add the following entry mapping `aiops.local` to the Vagrant master VM's IP address:

```text
192.168.56.24  aiops.local
```

### Step 4: Access via Domain

Now open your web browser on your host machine and navigate to:
**`http://aiops.local`**

You should see your streamlit application loading successfully through standard HTTP port 80!

---

## Troubleshooting Ingress

If `http://aiops.local` fails to load, check the following:
1. **Can you ping the master IP?** (`ping 192.168.56.24`)
2. **Is the ingress class correct?** Run `kubectl describe ingress aiops-assistant-ingress` and ensure the Class is listed as `nginx`.
3. **Are the ingress pods running?** Run `kubectl get pods -n ingress-nginx` to make sure the controller hasn't crashed.

---

## What's Next

Currently, if you try to query the assistant, it will fail because the OpenAI API Key is not set inside the pods. In the next lesson, we will configure **Kubernetes Secrets** to securely inject our API credentials.
