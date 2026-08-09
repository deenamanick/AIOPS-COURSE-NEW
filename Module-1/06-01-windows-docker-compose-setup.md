# AIOps Module 1 — RAG Demo Stack
# Runs on aiops-control VM (192.168.56.10)
# Access Streamlit UI from host: http://localhost:8501

services:

  # ---------------------------------------------------------------------------
  # ChromaDB — Vector Database
  # Start this first before rag-app
  # ---------------------------------------------------------------------------
  chromadb:
    image: chromadb/chroma:0.5.23       # Pinned version — stable & v2 API
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

  # ---------------------------------------------------------------------------
  # RAG App — Streamlit UI
  # Waits for ChromaDB to be healthy before starting
  # ---------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# Volumes
# -----------------------------------------------------------------------------
volumes:
  chroma-data:
    driver: local

# -----------------------------------------------------------------------------
# Networks
# -----------------------------------------------------------------------------
networks:
  rag-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/24
