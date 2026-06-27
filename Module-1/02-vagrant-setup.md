# 02 — Vagrant & VirtualBox Setup

## Prerequisites

Install on your host machine:

| Tool | Download | Verify |
|---|---|---|
| VirtualBox | [virtualbox.org/wiki/Downloads](https://www.virtualbox.org/wiki/Downloads) | `VBoxManage --version` |
| Vagrant | [developer.hashicorp.com/vagrant/downloads](https://developer.hashicorp.com/vagrant/downloads) | `vagrant --version` |

---

## The Vagrantfile

The `Vagrantfile` in this directory defines 2 VMs. Here's a walkthrough of the key sections:

### VM Definitions

```ruby
config.vm.define "aiops-control" do |control|
  control.vm.box = "bento/ubuntu-22.04"          # Ubuntu 22.04 base image
  control.vm.hostname = "aiops-control"
  control.vm.network "private_network", ip: "192.168.56.10"  # Static IP on host-only network
```

- **`bento/ubuntu-22.04`** — A well-maintained Vagrant box with VirtualBox Guest Additions pre-installed
- **`private_network`** — Creates a host-only network so VMs can talk to each other and your host can reach them

### Port Forwarding

```ruby
  control.vm.network "forwarded_port", guest: 8501, host: 8501, auto_correct: true  # Streamlit
```

This allows you to access services running inside the VM from your host browser:
- `http://localhost:8501` → Streamlit RAG UI (aiops-control)
- `http://localhost:8081` → Nginx (app-server)

### Resource Allocation

```ruby
  control.vm.provider "virtualbox" do |vb|
    vb.memory = "2048"    # 2GB RAM
    vb.cpus = 2           # 2 CPU cores
  end
```

| VM | RAM | CPUs | Reason |
|---|---|---|---|
| aiops-control | 2048 MB | 2 | Runs Docker Compose (Streamlit + ChromaDB) |
| app-server | 1024 MB | 1 | Runs Flask + Nginx (lightweight) |

### Provisioning

```ruby
  control.vm.provision "shell", path: "scripts/setup-control.sh"
```

On first `vagrant up`, Vagrant runs the shell script to install Docker, Node Exporter, etc.

---

## Lab: Spin Up the VMs

### Step 1: Start the VMs

```bash
cd Module-1
vagrant up
```

This downloads the `bento/ubuntu-22.04` box (first time only, ~700MB), creates both VMs, and runs the provisioning scripts. Takes 5-10 minutes.

### Step 2: Check status

```bash
vagrant status
```

Expected output:
```
Current machine states:
aiops-control             running (virtualbox)
app-server                running (virtualbox)
```

### Step 3: SSH into VMs

```bash
# SSH into the control VM
vagrant ssh aiops-control

# In another terminal — SSH into the app-server
vagrant ssh app-server
```

### Step 4: Test inter-VM networking

From `aiops-control`:
```bash
ping -c 3 192.168.56.11    # Should reach app-server
```

From `app-server`:
```bash
ping -c 3 192.168.56.10    # Should reach aiops-control
```

### Step 5: Test host access

From your host machine:
```bash
curl http://192.168.56.10:9100/metrics | head -5   # Node Exporter on control
curl http://192.168.56.11:9100/metrics | head -5   # Node Exporter on app-server
```

---

## Vagrant Cheat Sheet

| Command | Action |
|---|---|
| `vagrant up` | Create and start VMs |
| `vagrant halt` | Stop VMs (preserves data) |
| `vagrant destroy -f` | Delete VMs completely |
| `vagrant ssh <name>` | SSH into a VM |
| `vagrant status` | Show VM states |
| `vagrant provision` | Re-run provisioning scripts |
| `vagrant reload` | Restart VMs (applies Vagrantfile changes) |
| `vagrant snapshot save <name> <snapshot>` | Save VM state |
| `vagrant snapshot restore <name> <snapshot>` | Restore VM state |

---

## Concepts

| Concept | What it means |
|---|---|
| **Vagrant** | Tool that automates VM lifecycle — create, configure, destroy with code |
| **Vagrantfile** | Ruby DSL config file — defines VMs, networking, provisioning |
| **Box** | Pre-built VM image (like a Docker image but for VMs) |
| **Provisioner** | Script that runs on first `vagrant up` to install software |
| **Host-only network** | Private network between host and VMs — not internet-facing |
| **Port forwarding** | Maps a host port to a VM port — allows host browser access |
| **Hypervisor** | Software that creates/manages VMs (VirtualBox, VMware, KVM) |

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `vagrant up` hangs | Enable VT-x/AMD-V in BIOS |
| Port conflict | Change host port in Vagrantfile or set `auto_correct: true` |
| Box download slow | Use `vagrant box add bento/ubuntu-22.04` separately |
| VMs can't ping each other | Check VirtualBox Host-Only Network adapter exists in VirtualBox settings |
| Provisioning failed | Run `vagrant provision <vm-name>` to retry |
