# Module 3: Deployment — Docker & Kubernetes

Welcome to Module 3! In Module 2, you containerized the AIOps assistant using Docker. While Docker is fantastic for running containers locally, production environments require orchestration. In this module, you will learn **why** and **how** Kubernetes is used in production. You will deploy the assistant to a Kubernetes cluster, configure services and ingress routing, manage API keys using Kubernetes secrets, set resource limits, and simulate operational issues like Out-of-Memory (OOM) situations and image pull errors.

---

## Learning Objectives

By the end of this module, you will be able to:
1. Explain why Kubernetes is needed to orchestrate containerized applications in production.
2. Configure Kubernetes **Deployments** and understand how they manage **Pods** and **ReplicaSets**.
3. Create **Services** (ClusterIP, NodePort) to manage internal and external network traffic.
4. Implement an **Nginx Ingress Controller** to route HTTP traffic via path-based routing.
5. Securely store and inject sensitive parameters (like OpenAI API keys) using **Kubernetes Secrets**.
6. Set CPU/Memory **Requests and Limits** for AI/ML workloads and troubleshoot **Out-of-Memory (OOM)** failures.
7. Perform basic cluster troubleshooting and appreciate Kubernetes' self-healing capabilities.

---

## Prerequisites

- ✅ Module 2 completed (you should have built the containerized assistant image)
- ✅ A host machine with at least **8GB RAM** (16GB recommended if spinning up the 3-VM Vagrant cluster)
- ✅ An OpenAI API Key ([platform.openai.com](https://platform.openai.com))
- ✅ VirtualBox and Vagrant installed (for the multi-node VM lab option) OR a local tool like Minikube / Kind (for resource-limited machines)

---

## Lab Architecture

In this module, you will transition the application from a standalone Docker container into a fully managed Kubernetes cluster:

```
                  ┌──────────────────────────────────────────────────────────┐
                  │                 KUBERNETES CLUSTER                       │
                  │                                                          │
                  │   ┌──────────────────────────────────────────────────┐   │
                  │   │                    Ingress                       │   │
                  │   │           (nginx-ingress-controller)             │   │
                  │   └────────────────────────┬─────────────────────────┘   │
                  │                            │ (routes http://aiops.local) │
                  │                            ▼                             │
                  │   ┌──────────────────────────────────────────────────┐   │
                  │   │                    Service                       │   │
                  │   │             (NodePort / ClusterIP)               │   │
                  │   └────────────────────────┬─────────────────────────┘   │
                  │              ┌─────────────┴─────────────┐               │
                  │              ▼                           ▼               │
                  │   ┌───────────────────────┐   ┌───────────────────────┐  │
                  │   │         Pod 1         │   │         Pod 2         │  │
                  │   │  (aiops-assistant)    │   │  (aiops-assistant)    │  │
                  │   │  Memory Limit: 512Mi  │   │  Memory Limit: 512Mi  │  │
                  │   └──────────┬────────────┘   └──────────┬────────────┘  │
                  │              │ (Env Inject)              │ (Env Inject)  │
                  │              ◄─────────────┬─────────────►               │
                  │                            │                             │
                  │               ┌────────────┴────────────┐                │
                  │               │         Secret          │                │
                  │               │    (OPENAI_API_KEY)     │                │
                  │               └─────────────────────────┘                │
                  └──────────────────────────────────────────────────────────┘
```

---

## How to Set Up the Lab

Depending on your host machine's hardware capabilities, select **one** of the two lab options:

### Option A: The Multi-Node Vagrant Cluster (Recommended)
This option creates a realistic production-like environment with 3 Ubuntu VMs (1 Master node, 2 Worker nodes).
1. Navigate to the `lab/` folder:
   ```bash
   cd Module-3/lab
   ```
2. Start the VMs (this will take 5-10 minutes to download images and provision Kubernetes):
   ```bash
   vagrant up
   ```
3. SSH into the master node:
   ```bash
   vagrant ssh master
   ```
4. Verify the cluster is up:
   ```bash
   kubectl get nodes
   ```

### Option B: Minikube / Kind (Lightweight Alternative)
If your host machine is resource-constrained (e.g., less than 12GB available RAM), run a single-node local Kubernetes cluster.
1. Install Minikube (see [minikube.sigs.k8s.io](https://minikube.sigs.k8s.io)) or Kind (see [kind.sigs.k8s.io](https://kind.sigs.k8s.io)).
2. Start your cluster:
   ```bash
   minikube start --cpus=2 --memory=4096
   # OR
   kind create cluster
   ```

---

## Lessons in this Module

| # | Lesson | What You'll Do |
|---|---|---|
| 01 | [Docker to Kubernetes](./01-docker-to-kubernetes.md) | Understand the progression, learn core objects, and configure Deployments |
| 02 | [Services and Ingress](./02-services-and-ingress.md) | Expose the assistant via NodePort and configure Nginx Ingress routing |
| 03 | [ConfigMaps and Secrets](./03-configmaps-and-secrets.md) | Securely store and inject the OpenAI API key using K8s Secrets |
| 04 | [Resource Management Lab](./04-resource-management.md) | Set CPU/memory limits and trigger an Out-of-Memory (OOM) container restart |
| 05 | [Break/Fix Activities](./05-break-fix.md) | Delete pods to observe self-healing, scale replicas, and debug image pull errors |
| 06 | [Bonus Lecture](./06-bonus-lecture.md) | Learn GPU scheduling, persistent database volumes, and production secret storage |

Let's get started with **01-docker-to-kubernetes.md**!
