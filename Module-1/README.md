# Module 1: AIOps Fundamentals & RAG Demo

Welcome to Module 1! This module introduces the **foundations of AIOps** — what it is, why it matters, and how AI assists IT operations teams. You'll build a real multi-VM lab, deploy a sample application, and create an AI-powered incident assistant using RAG.

## 📂 Folder Contents

| File | Type | Description |
|---|---|---|
| `01-aiops-fundamentals.md` | Theory | AIOps lifecycle, SRE, monitoring vs observability |
| `02-vagrant-setup.md` | Lab | Vagrantfile, spin up 2 VMs, SSH, networking |
| `03-linux-ops-essentials.md` | Lab | top, systemctl, journalctl, ss, curl |
| `04-app-deployment.md` | Lab | Flask + Nginx on app-server |
| `05-node-exporter.md` | Lab | Install Prometheus Node Exporter on both VMs |
| `06-docker-compose-intro.md` | Lab | Docker Compose basics for the RAG stack |
| `07-rag-demo.md` | Lab | RAG incident assistant (Jaccard + Streamlit + bonus ChromaDB) |
| `08-break-fix.md` | Lab | Break/Fix troubleshooting exercises |
| `09-bonus-lecture.md` | Bonus | DORA metrics, architecture diagram, RFC writing, AIOps improvement proposals |

## 🏗️ Architecture

```
Host Machine
├── http://localhost:8501  → Streamlit RAG UI
├── http://localhost:8081  → Nginx (app-server)
│
├── VM: aiops-control (192.168.56.10)
│   ├── Docker Compose
│   │   ├── Streamlit App (8501)
│   │   ├── RAG Engine (Jaccard / ChromaDB)
│   │   └── ChromaDB (8000) — bonus
│   └── Node Exporter (9100)
│
└── VM: app-server (192.168.56.11)
    ├── Nginx (80) → Flask (5000)
    └── Node Exporter (9100)
```

## 🛠 Tech Stack

| Tool | Purpose |
|---|---|
| Vagrant + VirtualBox | VM provisioning |
| Ubuntu 22.04 (bento) | Base OS |
| Docker + Docker Compose | Container orchestration for RAG demo |
| Flask + Gunicorn | Sample web application |
| Nginx | Reverse proxy |
| Node Exporter | Prometheus metrics agent |
| Streamlit | RAG assistant UI |
| Python (Jaccard / ChromaDB) | Incident similarity search |

## ⚡ Quick Start

```bash
cd Module-1
vagrant up          # Spin up both VMs (~5-10 min)
vagrant status      # Verify running

# Test app-server
curl http://localhost:8081/health

# SSH into control and start RAG demo
vagrant ssh aiops-control
cd /opt/rag-demo
docker compose up -d

# Open in browser
# http://localhost:8501
```

## 📋 Prerequisites

- VirtualBox installed
- Vagrant installed
- 4GB+ free RAM on host
- Internet access (for downloading box + Docker images)
