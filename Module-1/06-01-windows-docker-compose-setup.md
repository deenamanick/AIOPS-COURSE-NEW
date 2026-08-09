### AIOps Course | Module 1

---

## Overview
This document covers the Docker Compose configuration
for the RAG demo stack running on `aiops-control` VM.

---

## docker-compose.yml

```yaml
# AIOps Module 1 — RAG Demo Stack
# Runs on aiops-control VM (192.168.56.10)
# Access Streamlit UI from host: http://localhost:8501

services:

  # ChromaDB — Vector Database
  # Start this first before rag-app
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
  # Waits for ChromaDB to be healthy before starting
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

# Volumes
volumes:
  chroma-data:
    driver: local

# Networks
networks:
  rag-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/24
```

---

## Services Explained

| Service | Image | Port | Purpose |
|---|---|---|---|
| chromadb | chroma:0.5.23 | 8000 | Vector Database |
| rag-app | local build | 8501 | Streamlit UI |

---

## Key Configuration Decisions

### Why Pin ChromaDB to 0.5.23?
```
latest tag = unpredictable ❌
0.5.23     = stable + v2 API compatible ✅
```

### Why service_healthy?
```
service_started = RAG app starts before ChromaDB ready ❌
service_healthy = RAG app waits for ChromaDB ready     ✅
```

### Why Fixed Subnet?
```
Auto subnet = possible conflicts ❌
172.28.0.0/24 = dedicated, no conflicts ✅
```

---

## Usage

```bash
# Navigate to rag-demo:
cd /opt/rag-demo

# Start services:
sudo docker compose up -d

# Check status:
sudo docker ps

# View logs:
sudo docker compose logs -f

# Stop services:
sudo docker compose down
```

---

## Verify Services

```bash
# ChromaDB heartbeat:
curl http://localhost:8000/api/v2/heartbeat

# Expected:
# {"nanosecond heartbeat":...} ✅

# Streamlit health:
curl -s -o /dev/null -w "%{http_code}" \
http://localhost:8501/_stcore/health

# Expected: 200 ✅
```

---

## Access from Browser

```
Streamlit UI  → http://localhost:8501  ✅
ChromaDB API  → http://localhost:8000/api/v2/heartbeat ✅
