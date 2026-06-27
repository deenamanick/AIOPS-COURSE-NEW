# 06 — Docker Compose Introduction

## Why Docker Compose?

In Module 1, we use Docker Compose on `aiops-control` to run the RAG demo stack (Streamlit app + ChromaDB). Docker Compose lets you define and run multi-container applications with a single YAML file.

```
docker-compose.yml defines:
  ├── rag-app     (Streamlit + Python RAG engine)
  └── chromadb    (Vector database — bonus)
```

---

## Verify Docker is Installed

```bash
vagrant ssh aiops-control

docker --version
docker compose version
```

---

## Docker Compose Basics

### File Structure

The `rag-demo/docker-compose.yml` defines our stack:

```yaml
services:
  rag-app:
    build: .                    # Build from Dockerfile in current directory
    ports:
      - "8501:8501"             # Expose Streamlit on port 8501
    volumes:
      - ./incidents.csv:/app/incidents.csv:ro   # Mount CSV (read-only)
    depends_on:
      chromadb:
        condition: service_started

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chroma-data:/chroma/chroma    # Persist data across restarts
```

### Key Concepts

| Concept | Meaning |
|---|---|
| `services` | Each container in your stack |
| `build: .` | Build a Docker image from the `Dockerfile` in the current directory |
| `image: chromadb/chroma` | Pull a pre-built image from Docker Hub |
| `ports: "8501:8501"` | Map host port → container port |
| `volumes` | Mount files/directories into the container, or persist container data |
| `depends_on` | Start this service only after the dependency is running |
| `networks` | Containers on the same network can reach each other by service name |

---

## Lab: Run the RAG Stack

### Step 1: Copy RAG demo files to the VM

Since we disabled synced folders, we need to get the files onto the VM. Option A (SCP from host):

```bash
# From your host machine
cd Module-1
vagrant ssh-config aiops-control > /tmp/ssh-config-control
scp -r -F /tmp/ssh-config-control rag-demo/* aiops-control:/opt/rag-demo/
```

Option B (clone from repo, if pushed to Git):
```bash
vagrant ssh aiops-control
cd /opt/rag-demo
git clone <your-repo> .
```

### Step 2: Build and start

```bash
vagrant ssh aiops-control
cd /opt/rag-demo

# Build the Streamlit container and start all services
docker compose up -d --build
```

### Step 3: Check status

```bash
docker compose ps
```

Expected:
```
NAME              IMAGE                    STATUS
aiops-rag-app     rag-demo-rag-app         Up (healthy)
aiops-chromadb    chromadb/chroma:latest   Up
```

### Step 4: View logs

```bash
# All services
docker compose logs -f

# Just the RAG app
docker compose logs -f rag-app
```

### Step 5: Access from host browser

Open: **http://localhost:8501**

---

## Essential Docker Compose Commands

| Command | Action |
|---|---|
| `docker compose up -d` | Start all services in background |
| `docker compose up -d --build` | Rebuild images and start |
| `docker compose down` | Stop and remove containers |
| `docker compose ps` | Show running containers |
| `docker compose logs -f` | Follow logs from all services |
| `docker compose logs -f <service>` | Follow logs from one service |
| `docker compose restart <service>` | Restart a specific service |
| `docker compose exec <service> bash` | Shell into a running container |
| `docker compose pull` | Pull latest images |

---

## Debugging

```bash
# Container not starting? Check logs:
docker compose logs rag-app

# Port conflict?
ss -tlnp | grep 8501

# Rebuild from scratch:
docker compose down
docker compose up -d --build --force-recreate

# Clean up everything (images, volumes):
docker compose down -v --rmi all
```

---

## What's Next

With Docker Compose running, proceed to **07-rag-demo.md** to understand the RAG engine, test incident queries, and explore the ChromaDB bonus.
