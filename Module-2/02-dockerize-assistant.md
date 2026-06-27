# 02 — Dockerize the AIOps Assistant

In Module 1, we used a basic Dockerfile to containerize the RAG demo. Now we will write an **upgraded Dockerfile** for the Module 2 assistant, which includes heavier AI dependencies (Sentence-Transformers, OpenAI SDK).

---

## Why Docker for AI/ML Apps?

| Challenge | Without Docker | With Docker |
|---|---|---|
| "It works on my machine" | Different Python versions, missing libraries | Identical environment everywhere |
| Dependency conflicts | `sentence-transformers` needs specific `torch` version | Isolated — no conflicts with system Python |
| Model download time | Downloads 90MB model on every fresh install | Pre-downloaded into the image layer |
| Reproducibility | "Which pip packages did I install again?" | `requirements.txt` locked in the image |

---

## The Dockerfile

In Module 1, our Dockerfile was simple — just `pip install` and run Streamlit. The Module 2 Dockerfile adds two key upgrades:

1. **Build dependencies** for ChromaDB's C extensions
2. **Pre-downloading the embedding model** so it doesn't download on every container start

Create a file named `Dockerfile` in your `lab/` folder and copy the following:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install build dependencies for ChromaDB and sentence-transformers
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model so it doesn't download on every container start
# This creates a cached layer — rebuilds are fast as long as the model doesn't change
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY . .

EXPOSE 8501

# Health check — Streamlit exposes a health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
```

### Line-by-Line Explanation

| Line | Purpose |
|---|---|
| `FROM python:3.10-slim` | Lightweight Python base image (much smaller than full `python:3.10`) |
| `build-essential` | Required for compiling ChromaDB's C/C++ extensions |
| `COPY requirements.txt .` then `RUN pip install` | Install dependencies BEFORE copying code — Docker caches this layer |
| `RUN python -c "... SentenceTransformer(...)"` | Pre-download the 90MB AI model into the image. Without this, every container restart downloads it again |
| `HEALTHCHECK` | Docker will ping Streamlit's health endpoint every 30s. If it fails 3 times, Docker marks the container as unhealthy |
| `--server.address 0.0.0.0` | Listen on all interfaces so the host browser can reach the container |

### Module 1 vs Module 2 Dockerfile

| Feature | Module 1 Dockerfile | Module 2 Dockerfile |
|---|---|---|
| Base image | `python:3.11-slim` | `python:3.10-slim` |
| Build deps | Not needed (simple packages) | `build-essential` for C extensions |
| Model pre-download | Not needed | ✅ Caches 90MB sentence-transformer model |
| Health check | ✅ Yes | ✅ Yes (longer start period for model loading) |
| Start period | 30s | 60s (model loading takes longer) |

---

## The Docker Compose File

Create a file named `docker-compose.yml` in your `lab/` folder:

```yaml
services:
  aiops-assistant:
    build: .
    container_name: module2-assistant
    ports:
      - "8501:8501"
    volumes:
      - ./incidents.csv:/app/incidents.csv:ro
      - ./.env:/app/.env:ro
    restart: unless-stopped
    environment:
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

### Key Decisions

| Config | Why |
|---|---|
| `volumes: ./incidents.csv:/app/incidents.csv:ro` | Mount CSV as read-only — you can regenerate data without rebuilding the image |
| `volumes: ./.env:/app/.env:ro` | Mount the `.env` file so the OpenAI API key is available inside the container |
| `restart: unless-stopped` | If the container crashes, Docker auto-restarts it (resilience!) |
| No separate ChromaDB service | We use `EphemeralClient()` (in-memory) for this lab. Production would use a separate ChromaDB container |

---

## Lab: Build and Run

### Step 1: Build the Image

```bash
cd /opt/module2-lab
docker compose build
```

This will take **3-5 minutes** the first time (downloading Python packages and the AI model). Subsequent builds will be fast thanks to Docker layer caching.

Watch for:
```
 => [4/6] RUN pip install --no-cache-dir -r requirements.txt
 => [5/6] RUN python -c "from sentence_transformers ..."     ← This downloads the model
```

### Step 2: Start the Container

```bash
docker compose up -d
```

### Step 3: Verify

```bash
# Check container is running
docker compose ps
```

Expected:
```
NAME                  IMAGE                     STATUS
module2-assistant     module2-lab-aiops-...     Up (healthy)
```

```bash
# Check logs
docker compose logs -f aiops-assistant
```

You should see Streamlit starting:
```
  You can now view your Streamlit app in your browser.
  URL: http://0.0.0.0:8501
```

### Step 4: Access from Host Browser

Open: **http://localhost:8501**

You should see the AIOps Assistant with a text area for incident input and a sidebar for settings.

---

## Docker Commands Reference

| Command | Action |
|---|---|
| `docker compose up -d --build` | Rebuild image and start |
| `docker compose down` | Stop and remove container |
| `docker compose logs -f` | Follow live logs |
| `docker compose restart` | Restart (e.g., after changing `.env`) |
| `docker compose exec aiops-assistant bash` | Shell into the running container |
| `docker image ls` | Check image size |

---

## What's Next

With the container running, proceed to **03-chromadb-vector-search.md** to understand how the vector search engine works inside the app.
