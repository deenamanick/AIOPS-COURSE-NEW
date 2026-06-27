#!/bin/bash
# =============================================================================
# AIOps Module 1 — aiops-control VM Provisioning
# Installs: Docker, Docker Compose, Node Exporter, Python3
# =============================================================================

set -e

echo ">>> Updating system packages..."
apt-get update -y
apt-get install -y \
  python3-pip curl gnupg lsb-release apt-transport-https \
  ca-certificates software-properties-common git

# --- Docker ---
echo ">>> Installing Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable docker
systemctl start docker
usermod -aG docker vagrant

# --- Node Exporter ---
echo ">>> Installing Node Exporter..."
NODE_EXPORTER_VERSION="1.7.0"
cd /tmp
curl -LO "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar xzf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
cp "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" /usr/local/bin/

# Create systemd service for Node Exporter
cat > /etc/systemd/system/node_exporter.service <<EOF
[Unit]
Description=Prometheus Node Exporter
After=network.target

[Service]
User=nobody
ExecStart=/usr/local/bin/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter

# --- RAG Demo Directory ---
echo ">>> Setting up RAG demo directory..."
mkdir -p /opt/rag-demo
chown -R vagrant:vagrant /opt/rag-demo

echo ">>> aiops-control provisioning complete!"
echo "    Docker:        $(docker --version)"
echo "    Node Exporter: http://192.168.56.10:9100/metrics"
