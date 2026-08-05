# Module 4: Production Ops — CI/CD, Testing & Scaling

Welcome to Module 4! In Module 3, you deployed the AIOps assistant to a Kubernetes cluster, configured services, ingress, and secrets. Your application is now running in production — but how do you **safely ship new changes** to it? In this module, you will build a complete **CI/CD pipeline** using GitHub Actions, write **automated tests** for ML/LLM-adjacent components, configure **Horizontal Pod Autoscaling (HPA)** to handle traffic spikes, and learn the **DORA metrics** that elite SRE teams use to measure engineering velocity.

---

## Learning Objectives

By the end of this module, you will be able to:
1. Build a CI/CD pipeline for AI/ML applications using **GitHub Actions** (lint → test → build → deploy).
2. Write **automated tests** for ML and LLM-adjacent components (unit, integration, and golden dataset tests).
3. Set up basic **monitoring and health checks** for production workloads.
4. Configure **Horizontal Pod Autoscaler (HPA)** to automatically scale Kubernetes pods based on CPU utilization.
5. Understand **deployment strategies** (rolling update, blue-green, canary) and when to use each.
6. Measure engineering performance using the **DORA metrics** framework.

---

## Prerequisites

- ✅ Module 3 completed (you should have a working Kubernetes cluster with the assistant deployed)
- ✅ A GitHub account with a repository for the AIOps assistant
- ✅ `kubectl` configured to access your cluster (Vagrant, Minikube, or Kind)
- ✅ Kubernetes Metrics Server installed (instructions provided in Lesson 04)
- ✅ `hey` or `wrk` HTTP load testing tool installed on your host machine

---

## Lab Architecture

In this module, you will layer a CI/CD pipeline and autoscaling on top of the Kubernetes deployment from Module 3:

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │                        GITHUB ACTIONS PIPELINE                       │
  │                                                                      │
  │   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌───────────────┐   │
  │   │   Lint   │──►│   Test   │──►│  Build   │──►│    Deploy     │   │
  │   │ (flake8) │   │ (pytest) │   │ (Docker) │   │  (kubectl)    │   │
  │   └──────────┘   └──────────┘   └──────────┘   └───────┬───────┘   │
  └─────────────────────────────────────────────────────────┼──────────┘
                                                            │
                                                            ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │                       KUBERNETES CLUSTER                             │
  │                                                                      │
  │   ┌──────────────────────────────────────────────────────────────┐   │
  │   │                 Horizontal Pod Autoscaler                    │   │
  │   │          (Target CPU: 70%, Min: 2, Max: 5 Pods)             │   │
  │   └──────────────────────────────┬───────────────────────────────┘   │
  │                                  │ (monitors & scales)               │
  │              ┌───────────────────┴───────────────────┐               │
  │              ▼                   ▼                   ▼               │
  │   ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐    │
  │   │      Pod 1       │ │      Pod 2       │ │    Pod 3 (new)   │    │
  │   │ (aiops-assistant)│ │ (aiops-assistant)│ │ (auto-scaled)    │    │
  │   └──────────────────┘ └──────────────────┘ └──────────────────┘    │
  └──────────────────────────────────────────────────────────────────────┘
```

---

## How to Set Up the Lab

### GitHub Repository Setup
If you haven't already, push your AIOps assistant codebase (from Module 2) to a GitHub repository:
```bash
cd Module-2/lab/app
git init
git add .
git commit -m "Initial commit: AIOps assistant"
git remote add origin https://github.com/YOUR_USERNAME/aiops-assistant.git
git push -u origin main
```

### Kubernetes Cluster
Ensure your Module 3 cluster is running. If using Vagrant:
```bash
cd Module-3/lab
vagrant up
vagrant ssh master
kubectl get nodes   # All nodes should be Ready
```

---

## Lessons in this Module

| # | Lesson | What You'll Do |
|---|---|---|
| 01 | [CI/CD Pipeline with GitHub Actions](./01-cicd-pipeline.md) | Build a complete lint → test → build → deploy pipeline triggered on every push |
| 02 | [Testing AI/ML Components](./02-testing-ai-ml.md) | Write 5 automated tests: unit tests, integration tests, and a golden dataset accuracy test |
| 03 | [Monitoring & Health Checks](./03-monitoring-health-checks.md) | Set up liveness/readiness probes, resource visibility, and basic alerting |
| 04 | [Autoscaling with HPA](./04-autoscaling-hpa.md) | Configure Horizontal Pod Autoscaler and generate synthetic load to watch pods scale |
| 05 | [Break/Fix Activities](./05-break-fix.md) | Push a broken test to block CI, simulate a traffic spike, and observe autoscaler response |
| 06 | [Bonus Lecture](./06-bonus-lecture.md) | Learn DORA metrics, deployment strategies (blue-green, canary), and production gate patterns |

Let's get started with **01-cicd-pipeline.md**!
