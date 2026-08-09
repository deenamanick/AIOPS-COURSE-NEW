# AIOps Module 1 — Multi-VM Lab Environment

## Overview
This lab sets up a multi-VM environment for AIOps training. It includes a RAG (Retrieval Augmented Generation) demo stack running on two VMs managed by Vagrant and VirtualBox.

---

## Architecture

```text
Windows Host (PowerShell as Administrator)
├── VirtualBox
│     ├── aiops-control (192.168.56.10)
│     │     ├── Docker CE
│     │     ├── Docker Compose Plugin
│     │     ├── Streamlit RAG App  → localhost:8501
│     │     ├── ChromaDB           → localhost:8000
│     │     └── Node Exporter      → localhost:9100
│     │
│     └── app-server (192.168.56.11)
│           ├── Nginx              → localhost:8081
│           ├── Flask App          → localhost:5000
│           └── Node Exporter      → localhost:9101
```

---

## Prerequisites

| Tool | Version | Download |
|---|---|---|
| VirtualBox | 7.0.x | https://www.virtualbox.org |
| Vagrant | 2.4.x | https://www.vagrantup.com |
| PowerShell | 5.1+ | Built into Windows |
| Git | Latest | https://git-scm.com |

---

## Important Notes for Windows Users

### ⚠️ Always Use PowerShell as Administrator
* ❌ Do **NOT** use WSL2 for Vagrant commands
* ❌ Do **NOT** use GitBash for `vagrant upload`
* ✅ Always use **PowerShell as Administrator**

### ⚠️ Hyper-V Must Be Disabled

```powershell
# Run in PowerShell as Administrator:
bcdedit /set hypervisorlaunchtype off

# Restart Windows after running this command:
shutdown /r /t 0
```

> **Note:** Disabling Hyper-V will stop WSL2 and Docker Desktop.  
> To re-enable later, run: `bcdedit /set hypervisorlaunchtype auto`

### ⚠️ Add VirtualBox to PATH

1. Open Windows Search → Search for **Environment Variables**
2. Go to **System Variables** → **Path** → **Edit** → **New**
3. Add: `C:\Program Files\Oracle\VirtualBox`
4. Click **OK** → **OK** → **OK**
5. Restart PowerShell

---

## Project Structure

```text
Module-1/
    ├── Vagrantfile                 # VM definitions
    ├── README.md                   # This file
    ├── rag-demo/                   # RAG application
    │     ├── docker-compose.yml    # Docker services
    │     ├── app.py                # Streamlit app
    │     ├── requirements.txt      # Python dependencies
    │     ├── Dockerfile            # Container build
    │     └── incidents.csv         # Sample data
    └── scripts/
            ├── setup-control.sh    # aiops-control provisioner
            └── setup-app.sh        # app-server provisioner
```

---

## VM Configuration

### `aiops-control` (192.168.56.10)
| Setting | Value |
|---|---|
| OS | Ubuntu 22.04 |
| RAM | 2048 MB |
| CPUs | 2 |
| IP | 192.168.56.10 |
| Role | Docker, RAG Demo, Management |

### `app-server` (192.168.56.11)
| Setting | Value |
|---|---|
| OS | Ubuntu 22.04 |
| RAM | 1024 MB |
| CPUs | 1 |
| IP | 192.168.56.11 |
| Role | Nginx, Flask App |

### Port Forwarding

| Service | Host Port | VM Port | VM |
|---|---|---|---|
| Streamlit UI | 8501 | 8501 | aiops-control |
| ChromaDB API | 8000 | 8000 | aiops-control |
| Node Exporter | 9100 | 9100 | aiops-control |
| Nginx | 8081 | 80 | app-server |
| Node Exporter | 9101 | 9100 | app-server |

---

## Vagrantfile

```ruby
# -*- mode: ruby -*-
# vi: set ft=ruby :

# =============================================================================
# AIOps Course — Module 1: Multi-VM Lab Environment
#
# Provider: VirtualBox
#
# VMs:
#   aiops-control (192.168.56.10) — Docker, Streamlit RAG, Node Exporter
#   app-server    (192.168.56.11) — Nginx, Flask app, Node Exporter
#
# Port Forwarding (host → guest):
#   localhost:8501  → aiops-control:8501  (Streamlit UI)
#   localhost:8000  → aiops-control:8000  (ChromaDB)
#   localhost:8081  → app-server:80       (Nginx)
#   localhost:9100  → aiops-control:9100  (Node Exporter)
#   localhost:9101  → app-server:9100     (Node Exporter)
# =============================================================================

Vagrant.configure("2") do |config|

  # Validate provisioning scripts exist before starting
  ["scripts/setup-control.sh", "scripts/setup-app.sh"].each do |script|
    raise "Missing provisioning script: #{script}" unless File.exist?(script)
  end

  # ---------------------------------------------------------------------------
  # VM 1: aiops-control — Docker, RAG demo, management node
  # ---------------------------------------------------------------------------
  config.vm.define "aiops-control" do |control|
    control.vm.box = "bento/ubuntu-22.04"
    control.vm.hostname = "aiops-control"
    control.vm.boot_timeout = 600

    # Private network
    control.vm.network "private_network", ip: "192.168.56.10"

    # Port forwarding
    control.vm.network "forwarded_port", guest: 8501, host: 8501, auto_correct: true  # Streamlit
    control.vm.network "forwarded_port", guest: 8000, host: 8000, auto_correct: true  # ChromaDB
    control.vm.network "forwarded_port", guest: 9100, host: 9100, auto_correct: true  # Node Exporter

    # Disable default synced folder
    control.vm.synced_folder ".", "/vagrant", disabled: true

    # VirtualBox resource allocation
    control.vm.provider "virtualbox" do |vb|
      vb.memory = "2048"
      vb.cpus = 2
      vb.name = "aiops-control"
      vb.gui = false
      vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
      vb.customize ["modifyvm", :id, "--natdnsproxy1", "on"]
      vb.customize ["modifyvm", :id, "--usb", "off"]
      vb.customize ["modifyvm", :id, "--usbehci", "off"]
    end

    # Provisioning script
    control.vm.provision "shell",
      path: "scripts/setup-control.sh",
      privileged: true
  end

  # ---------------------------------------------------------------------------
  # VM 2: app-server — Nginx + Flask sample application
  # ---------------------------------------------------------------------------
  config.vm.define "app-server" do |app|
    app.vm.box = "bento/ubuntu-22.04"
    app.vm.hostname = "app-server"
    app.vm.boot_timeout = 600

    # Private network
    app.vm.network "private_network", ip: "192.168.56.11"

    # Port forwarding
    app.vm.network "forwarded_port", guest: 80,   host: 8081, auto_correct: true  # Nginx
    app.vm.network "forwarded_port", guest: 9100, host: 9101, auto_correct: true  # Node Exporter

    # Disable default synced folder
    app.vm.synced_folder ".", "/vagrant", disabled: true

    # VirtualBox resource allocation
    app.vm.provider "virtualbox" do |vb|
      vb.memory = "1024"
      vb.cpus = 1
      vb.name = "app-server"
      vb.gui = false
      vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
      vb.customize ["modifyvm", :id, "--natdnsproxy1", "on"]
      vb.customize ["modifyvm", :id, "--usb", "off"]
      vb.customize ["modifyvm", :id, "--usbehci", "off"]
    end

    # Provisioning script
    app.vm.provision "shell",
      path: "scripts/setup-app.sh",
      privileged: true
  end
end
```

---

## Step-by-Step Setup Guide

### Step 1 — Clone Repository
Run in PowerShell as Administrator:
```powershell
git clone <your-repo-url>
cd Module-1
```

### Step 2 — Start VMs
Run in PowerShell as Administrator:
```powershell
vagrant up
```
*Expected output:*
```text
Bringing machine 'aiops-control' up with 'virtualbox' provider... ✅
Bringing machine 'app-server' up with 'virtualbox' provider...    ✅
```

### Step 3 — Verify VMs are Running
```powershell
vagrant status
```
*Expected:*
```text
aiops-control    running (virtualbox) ✅
app-server       running (virtualbox) ✅
```

### Step 4 — Create RAG Demo Folder on `aiops-control`
> **IMPORTANT:** Must be done from PowerShell.

Fix permissions on `aiops-control`:
```powershell
vagrant ssh aiops-control -c "sudo mkdir -p /opt/rag-demo && sudo chown -R vagrant:vagrant /opt/rag-demo && sudo chmod -R 755 /opt/rag-demo"
```

Verify folder created:
```powershell
vagrant ssh aiops-control -c "ls -la /opt/"
```
*Expected:* `drwxr-xr-x vagrant vagrant rag-demo ✅`

### Step 5 — Upload RAG Demo Files
> **IMPORTANT:** Must use PowerShell, NOT GitBash.

Upload `rag-demo` folder to `aiops-control`:
```powershell
vagrant upload rag-demo /opt/rag-demo aiops-control
```

Verify files uploaded:
```powershell
vagrant ssh aiops-control -c "ls -la /opt/rag-demo/"
```
*Expected output includes:*
* `docker-compose.yml` ✅
* `app.py` ✅
* `requirements.txt` ✅
* `Dockerfile` ✅
* `incidents.csv` ✅

### Step 6 — Install Docker on `aiops-control`

SSH into `aiops-control`:
```powershell
vagrant ssh aiops-control
```

Inside the `aiops-control` VM, run:
```bash
# Update system:
sudo apt-get update -y

# Install dependencies:
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker GPG key:
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository:
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker CE and Docker Compose Plugin:
sudo apt-get update -y
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-compose-plugin

# Add vagrant user to docker group:
sudo usermod -aG docker vagrant

# Enable and start Docker:
sudo systemctl enable docker
sudo systemctl start docker

# Verify installations:
docker --version
docker compose version
```

### Step 7 — Start RAG Demo Stack

Inside the `aiops-control` VM, run:
```bash
# Navigate to rag-demo:
cd /opt/rag-demo

# Verify docker-compose.yml exists:
cat docker-compose.yml

# Start services:
sudo docker compose up -d

# Check running containers:
sudo docker ps
```
*Expected:*
* `aiops-chromadb` → Up X minutes (healthy) ✅
* `aiops-rag-app` → Up X minutes (healthy) ✅

### Step 8 — Verify Services

Inside the `aiops-control` VM, run:
```bash
# Test ChromaDB heartbeat:
curl http://localhost:8000/api/v2/heartbeat
# Expected: {"nanosecond heartbeat":...} ✅

# Test ChromaDB version:
curl http://localhost:8000/api/v2/version
# Expected: "1.0.0" ✅

# Test Streamlit:
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/_stcore/health
# Expected: 200 ✅

# Exit VM:
exit
```

### Step 9 — Test from Windows Browser
Open your browser on Windows and check the following URLs:

* ✅ **Streamlit RAG UI:** [http://localhost:8501](http://localhost:8501)
* ✅ **ChromaDB Heartbeat:** [http://localhost:8000/api/v2/heartbeat](http://localhost:8000/api/v2/heartbeat)
* ✅ **ChromaDB Version:** [http://localhost:8000/api/v2/version](http://localhost:8000/api/v2/version)

---

## Docker Services (`aiops-control`)

### `docker-compose.yml`

```yaml
# AIOps Module 1 — RAG Demo Stack
# Runs on aiops-control VM (192.168.56.10)
# Access Streamlit UI from host: http://localhost:8501

services:

  # ChromaDB — Vector Database
  chromadb:
    image: chromadb/chroma:0.5.23
    container_name: aiops-chromadb
    ports:
      - "8000:8000"
    volumes:
      - chroma-data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE
      - CHROMA_SERVER_HOST=0.0.0.0
    restart: unless-stopped
    networks:
      - rag-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v2/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s

  # RAG App — Streamlit UI
  rag-app:
    build: .
    container_name: aiops-rag-app
    ports:
      - "8501:8501"
    volumes:
      - ./incidents.csv:/app/incidents.csv:ro
    environment:
      - RAG_ENGINE=jaccard
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
    depends_on:
      chromadb:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - rag-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

volumes:
  chroma-data:
    driver: local

networks:
  rag-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/24
```

---

## ChromaDB API Reference

| Endpoint | URL | Description |
|---|---|---|
| Heartbeat | `/api/v2/heartbeat` | Check if running |
| Version | `/api/v2/version` | Get version |
| Collections | `/api/v2/tenants/default_tenant/databases/default_database/collections` | List collections |

> ⚠️ **Warning:** ChromaDB v1 API is deprecated. Always use `/api/v2/` endpoints.

---

## Common Commands

### Vagrant Commands (PowerShell)

```powershell
# Check status:
vagrant status

# Start VMs:
vagrant up

# Stop VMs:
vagrant halt

# Restart VMs:
vagrant reload

# SSH into VM:
vagrant ssh aiops-control
vagrant ssh app-server

# Re-run provisioning:
vagrant provision aiops-control
vagrant provision app-server

# Destroy VMs:
vagrant destroy -f

# Upload files (PowerShell only):
vagrant upload <source> <destination> <vm-name>
```

### Docker Commands (Inside `aiops-control`)

```bash
# Check running containers:
docker ps

# Check all containers:
docker ps -a

# View logs:
docker compose logs -f

# Restart services:
docker compose restart

# Stop all services:
docker compose down

# Start all services:
docker compose up -d

# Rebuild and start:
docker compose build --no-cache
docker compose up -d
```

---

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| VM Stuck at "Waiting for machine to boot" | Hyper-V conflict | Disable Hyper-V via `bcdedit /set hypervisorlaunchtype off` and reboot |
| VBoxManage Not Found | PATH not set | Add `C:\Program Files\Oracle\VirtualBox` to System PATH |
| `vagrant upload` Permission Denied | `/opt` owned by root | Run `sudo chown -R vagrant:vagrant /opt/rag-demo` on the VM first |
| `vagrant upload` Sends to Wrong Path | Using GitBash | Switch to PowerShell as Administrator |
| ChromaDB v1 Deprecated | Latest image uses v2 API | Use `/api/v2/` endpoints instead of `/api/v1/` |
| Docker Not Found After Install | Group membership not applied | Run `newgrp docker` or re-login/re-SSH to VM |
| RAG App Shows Unhealthy | Container boot issue | Check logs using `docker logs aiops-rag-app --tail 50` and restart |

---

## Requirements Checklist

### Before running `vagrant up`:
- [ ] VirtualBox 7.0.x installed
- [ ] Vagrant 2.4.x installed
- [ ] Hyper-V disabled
- [ ] VirtualBox added to PATH
- [ ] PowerShell running as Administrator
- [ ] `scripts/setup-control.sh` exists
- [ ] `scripts/setup-app.sh` exists
- [ ] `rag-demo/` folder with all required files exists

### After `vagrant up`:
- [ ] Both VMs running (`vagrant status`)
- [ ] `/opt/rag-demo` folder created on `aiops-control`
- [ ] `rag-demo` files uploaded to `aiops-control`
- [ ] Docker CE installed on `aiops-control`
- [ ] Docker Compose Plugin installed on `aiops-control`
- [ ] `docker compose up -d` running successfully
- [ ] ChromaDB healthy (`curl /api/v2/heartbeat`)
- [ ] Streamlit accessible ([http://localhost:8501](http://localhost:8501))
  