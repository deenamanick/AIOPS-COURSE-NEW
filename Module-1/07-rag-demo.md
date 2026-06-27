# 07 — RAG Demo: AIOps Incident Assistant

## What is RAG?

**Retrieval-Augmented Generation (RAG)** combines information retrieval with AI generation. Instead of the AI hallucinating answers, it first **retrieves** relevant context from a knowledge base, then uses that context to **generate** an accurate answer.

```
User Query: "database connection pool exhausted"
         │
         ▼
┌─────────────────────┐
│  Retrieval Engine    │ → Search past incidents for similar descriptions
│  (Jaccard / ChromaDB)│
└─────────┬───────────┘
          │ Top 3 matches
          ▼
┌─────────────────────┐
│  Display Results    │ → Show root cause + resolution from past incidents
│  (Streamlit UI)     │ → In Module 2: feed to LLM for auto-generated RCA
└─────────────────────┘
```

In Module 1, we build the **Retrieval** part. In Module 2, we add LLM **Generation** for automated Root Cause Analysis.

---

## The Incident Dataset

File: `rag-demo/incidents.csv` — 32 real-world-style incident records.

| Column | Description | Example |
|---|---|---|
| `id` | Unique incident ID | 1 |
| `timestamp` | When it happened | 2024-01-15 02:30:00 |
| `severity` | critical / high / medium | critical |
| `service` | Affected service | database |
| `description` | What happened | MySQL connection pool exhausted causing 500 errors |
| `root_cause` | Why it happened | max_connections set to 50, insufficient for 2000 users |
| `resolution` | How it was fixed | Increased max_connections to 200, added PgBouncer |

---

## Part 1: Jaccard Similarity Search

### How Jaccard Works

**Jaccard similarity** measures the overlap between two sets of tokens:

```
Jaccard(A, B) = |A ∩ B| / |A ∪ B|

Example:
  Query tokens:    {database, connection, pool, exhausted}
  Incident tokens: {mysql, connection, pool, exhausted, causing, 500, errors, api, endpoints}

  Intersection: {connection, pool, exhausted} = 3
  Union: {database, mysql, connection, pool, exhausted, causing, 500, errors, api, endpoints} = 10

  Jaccard = 3/10 = 0.30
```

Higher score = more similar. The engine returns the top-k incidents sorted by score.

### The RAG Engine Code

File: `rag-demo/rag_engine.py`

Key functions:
- `load_incidents(csv_path)` — Read CSV, tokenize each description
- `tokenize(text)` — Lowercase, remove punctuation, remove stop words, return set of tokens
- `jaccard_similarity(set_a, set_b)` — Calculate `|A ∩ B| / |A ∪ B|`
- `search(query, incidents, top_k=3)` — Score all incidents, return top-k matches

### Test from CLI

```bash
vagrant ssh aiops-control
cd /opt/rag-demo

# Quick test (if Python is available directly)
docker compose exec rag-app python rag_engine.py
```

Expected output:
```
Loaded 32 incidents.

Query: "database connection pool exhausted"
  [critical] Score: 0.3   — MySQL connection pool exhausted causing 500 errors...
  [high]     Score: 0.18  — Database connection refused errors from application...
  [medium]   Score: 0.15  — Redis session store connection pool exhausted...
```

---

## Part 2: Streamlit UI

File: `rag-demo/streamlit_app.py`

### Access the UI

After running `docker compose up -d` (from lesson 06), open your host browser:

**http://localhost:8501**

### Features

1. **Search bar** — Type a query like "nginx returning 502 error"
2. **Engine selector** — Switch between Jaccard and ChromaDB (sidebar)
3. **Results** — Expandable cards showing severity, description, root cause, resolution
4. **Data explorer** — View the full incident dataset

### Test Queries to Try

| Query | Expected top match |
|---|---|
| "database connection pool exhausted" | Incident #1 — MySQL connection pool |
| "nginx 502 bad gateway" | Incident #2 — Flask crash causing 502 |
| "disk space full on server" | Incident #5 — Root disk at 100% |
| "SSL certificate expired" | Incident #6 — Certificate renewal failed |
| "CPU usage very high" | Incident #14 — Runaway cron job at 99% CPU |
| "memory leak application" | Incident #4 or #21 — Memory leak patterns |

---

## Part 3: Bonus — ChromaDB Vector Search 🆕

### Why Vector Search?

Jaccard similarity is **keyword-based** — it only matches exact words. It fails when:
- The query uses different words: "DB is slow" won't match "MySQL latency spike"
- Synonyms: "server crash" vs "service outage"
- Semantic meaning: "users can't log in" vs "authentication failure"

**ChromaDB** uses **embeddings** (vector representations of text) to find **semantically similar** incidents even without exact keyword matches.

### How It Works

```
"server running out of memory slowly"
         │
         ▼ (embedding model converts text to a 384-dimension vector)
  [0.023, -0.145, 0.892, ..., 0.034]
         │
         ▼ (cosine similarity with all stored vectors)
  Closest match: "Memory usage climbing steadily reaching 95% over 48 hours"
```

### Test ChromaDB

In the Streamlit sidebar, switch the engine to **ChromaDB (Vector)**. Try the same queries and compare:

| Query | Jaccard result | ChromaDB result |
|---|---|---|
| "server running out of memory slowly" | May not match (no exact keywords) | Matches incident #21 (memory climbing) |
| "users seeing errors on website" | Generic match | Matches incident #20 (403 errors) |
| "things are slow after an update" | Weak match | Matches incident #29 (TLS after OpenSSL update) |

### Limitations

- ChromaDB's default embedding model is basic — Module 2 uses Sentence-Transformers for better quality
- Vector search can return false positives for very short queries
- ChromaDB requires more resources than Jaccard (Docker container, persistent storage)

---

## Concepts

| Concept | What it means |
|---|---|
| **RAG** | Retrieval-Augmented Generation — retrieve context first, then generate answers |
| **Jaccard similarity** | Set overlap metric: `|A ∩ B| / |A ∪ B|` — simple, fast, keyword-based |
| **Tokenization** | Splitting text into individual words/tokens |
| **Stop words** | Common words (the, is, and) removed to reduce noise |
| **Embeddings** | Dense vector representations of text capturing semantic meaning |
| **ChromaDB** | Open-source vector database — stores and queries embeddings |
| **Cosine similarity** | Angle-based similarity between two vectors — used by ChromaDB |

---

## What's Next

- **Module 2**: Replace Jaccard with proper Sentence-Transformer embeddings + LLM integration for auto-generated Root Cause Analysis
- **Module 11**: Run the LLM locally using Ollama (no cloud API needed)
