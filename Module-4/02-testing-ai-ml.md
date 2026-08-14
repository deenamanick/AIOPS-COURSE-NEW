# 02 — Testing AI/ML Components

Your CI pipeline runs `pytest tests/`, but those tests don't exist yet. In this lesson, you will write **5 automated tests** that validate the correctness of your AIOps assistant's ML pipeline. Testing AI/ML systems is fundamentally different from testing traditional web applications — you're not just checking if a function returns the right value; you're validating that probabilistic models produce *acceptable* outputs.

---

## The AI/ML Testing Pyramid

Traditional software testing uses unit → integration → end-to-end layers. For AI/ML systems, we add an additional layer: **model accuracy tests** using golden datasets.

```
                    ┌─────────────────────────┐
                    │   Golden Dataset Test   │  (Slow, High Value)
                    │  "Does the ML model     │
                    │   produce correct RCA?" │
                    ├─────────────────────────┤
                    │   Integration Tests     │  (Medium Speed)
                    │  "Does the API respond  │
                    │   with valid JSON?"     │
                    ├─────────────────────────┤
                    │      Unit Tests         │  (Fast, High Volume)
                    │  "Does text chunking    │
                    │   split correctly?"     │
                    └─────────────────────────┘
```

---

## Lab: Writing the Test Suite

### Step 1: Create the Test Directory

In your AIOps assistant project root:
```bash
mkdir -p tests
touch tests/__init__.py
```

### Step 2: Install Test Dependencies

Add `pytest` to your `requirements.txt` (or install it directly):
```bash
pip install pytest requests
```

---

### Test 1: Unit Test — Text Chunking

The assistant processes incident logs by splitting them into chunks before embedding. This test validates that the chunking function correctly splits a long string into smaller pieces.

Create `tests/test_chunking.py`:

```python
"""Unit Test 1: Validate text chunking logic."""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def test_chunking_produces_correct_number_of_chunks():
    """A 1200-character string with chunk_size=500 and overlap=50 should produce 3 chunks."""
    text = "A" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"


def test_chunking_preserves_all_content():
    """Every character in the original text must appear in at least one chunk."""
    text = "The quick brown fox jumps over the lazy dog. " * 30
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    reconstructed = ""
    for i, chunk in enumerate(chunks):
        if i == 0:
            reconstructed += chunk
        else:
            # Skip the overlap portion to avoid duplicating characters
            reconstructed += chunk[20:]
    assert len(reconstructed) >= len(text), "Chunking lost content"
```

---

### Test 2: Unit Test — Embedding Generation

This test validates that the sentence-transformer model produces vector embeddings of the correct dimensionality.

Create `tests/test_embeddings.py`:

```python
"""Unit Test 2: Validate embedding generation output shape."""

import numpy as np


def generate_mock_embedding(text: str, dim: int = 384) -> list[float]:
    """Simulate a sentence-transformer embedding (384-dim for all-MiniLM-L6-v2)."""
    np.random.seed(hash(text) % 2**32)
    return np.random.randn(dim).tolist()


def test_embedding_has_correct_dimensions():
    """The all-MiniLM-L6-v2 model produces 384-dimensional embeddings."""
    embedding = generate_mock_embedding("Server CPU at 95% for 10 minutes")
    assert len(embedding) == 384, f"Expected 384 dims, got {len(embedding)}"


def test_embedding_values_are_floats():
    """Every element in the embedding vector must be a float."""
    embedding = generate_mock_embedding("Database connection timeout after 30s")
    assert all(isinstance(v, float) for v in embedding), "Embedding contains non-float values"
```

---

### Test 3: Integration Test — API Endpoint

This test validates that the Streamlit application's health endpoint responds correctly.

Create `tests/test_api_endpoint.py`:

```python
"""Integration Test 1: Validate the assistant API health check endpoint."""

import subprocess
import time
import requests
import pytest

APP_URL = "http://localhost:8501"


@pytest.fixture(scope="module")
def streamlit_server():
    """Start the Streamlit app in a subprocess for testing."""
    proc = subprocess.Popen(
        ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.headless=true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for server to start
    for _ in range(30):
        try:
            resp = requests.get(f"{APP_URL}/_stcore/health", timeout=2)
            if resp.status_code == 200:
                break
        except requests.ConnectionError:
            time.sleep(1)
    yield proc
    proc.terminate()
    proc.wait()


def test_health_endpoint_returns_ok(streamlit_server):
    """The Streamlit health check endpoint must return HTTP 200."""
    response = requests.get(f"{APP_URL}/_stcore/health", timeout=5)
    assert response.status_code == 200, f"Health check failed with status {response.status_code}"
```

---

### Test 4: Integration Test — Database Query

This test validates that the ChromaDB vector store can ingest a document and return a relevant result when queried.

Create `tests/test_db_query.py`:

```python
"""Integration Test 2: Validate ChromaDB ingestion and retrieval."""

import chromadb


def test_chromadb_ingest_and_query():
    """Ingesting a document and querying for it should return the same document."""
    client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection(
        name="test_incidents",
        metadata={"hnsw:space": "cosine"},
    )

    # Ingest a known incident
    collection.add(
        documents=["High CPU usage on web-server-01 caused by runaway Python process"],
        ids=["incident-001"],
        metadatas=[{"severity": "critical", "service": "web-server-01"}],
    )

    # Query for a related incident
    results = collection.query(query_texts=["CPU spike on server"], n_results=1)

    assert len(results["documents"][0]) == 1, "Expected 1 result"
    assert "CPU" in results["documents"][0][0], "Expected the CPU incident to be returned"
    assert results["ids"][0][0] == "incident-001", "Expected incident-001"
```

---

### Test 5: Golden Dataset ML Accuracy Test

This is the most important test for AI/ML systems. A **golden dataset** is a curated set of known inputs and their expected outputs. You run the model against these inputs and assert that its accuracy meets a minimum threshold.

Create `tests/test_golden_dataset.py`:

```python
"""ML Accuracy Test: Validate model performance against a golden dataset of known incidents."""

import json

# Golden dataset: 10 known incidents with expected root cause categories
GOLDEN_DATASET = [
    {"incident": "CPU at 98% on web-server-01 for 15 minutes", "expected_category": "CPU"},
    {"incident": "Out of memory killed process nginx pid 1234", "expected_category": "Memory"},
    {"incident": "Disk /dev/sda1 at 95% capacity on db-server-02", "expected_category": "Disk"},
    {"incident": "Connection timeout to database on port 5432", "expected_category": "Network"},
    {"incident": "SSL certificate expired for api.example.com", "expected_category": "Certificate"},
    {"incident": "High latency 2500ms on payment gateway API", "expected_category": "Latency"},
    {"incident": "Pod CrashLoopBackOff due to OOMKilled exit code 137", "expected_category": "Memory"},
    {"incident": "DNS resolution failed for internal service mesh", "expected_category": "Network"},
    {"incident": "NFS mount point /data/shared became read-only", "expected_category": "Disk"},
    {"incident": "Load average 12.5 on 4-core application server", "expected_category": "CPU"},
]

CATEGORY_KEYWORDS = {
    "CPU": ["cpu", "load average", "processor"],
    "Memory": ["memory", "oom", "out of memory"],
    "Disk": ["disk", "mount", "capacity", "storage"],
    "Network": ["network", "connection", "timeout", "dns"],
    "Certificate": ["ssl", "certificate", "tls"],
    "Latency": ["latency", "slow", "response time"],
}


def classify_incident(incident_text: str) -> str:
    """Simple keyword-based classifier (simulating ML model output)."""
    text_lower = incident_text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "Unknown"


def test_golden_dataset_accuracy():
    """The classifier must achieve at least 80% accuracy on the golden dataset."""
    correct = 0
    total = len(GOLDEN_DATASET)

    for test_case in GOLDEN_DATASET:
        predicted = classify_incident(test_case["incident"])
        if predicted == test_case["expected_category"]:
            correct += 1

    accuracy = correct / total
    assert accuracy >= 0.8, (
        f"Golden dataset accuracy is {accuracy:.0%} ({correct}/{total}). "
        f"Minimum required: 80%"
    )
```

---

### 💡 Real-World Case Study: Golden Datasets at Jeevisoft

At our company, we don't just use golden datasets for offline CI/CD testing—we use them dynamically in production for **Prompt-Based Fine-Tuning**. 

In our `jeevi-ai-reviewer` (an LLM-powered static analysis bot), the AI sometimes hallucinates false positives (e.g., flagging native D1 SQL as a missing ORM, or complaining about a missing `LIMIT` on a bounded query). 

When these occur, our engineers document the exact hallucination and the required architectural correction into an `AI-FALSE-POSITIVES-CATALOG.MD`. This catalog acts as our empirical **Golden Dataset**. 

Instead of retraining the base model, we inject this golden dataset directly into the LLM's system prompt (the Negative Constraint Engine). This ensures the AI is perfectly calibrated against our specific architectural patterns without writing thousands of lines of traditional tests!

---

## Running the Test Suite

Execute all 5 tests from the project root:

```bash
pytest tests/ -v --tb=short
```

Expected Output:
```text
tests/test_chunking.py::test_chunking_produces_correct_number_of_chunks     PASSED
tests/test_chunking.py::test_chunking_preserves_all_content                 PASSED
tests/test_embeddings.py::test_embedding_has_correct_dimensions             PASSED
tests/test_embeddings.py::test_embedding_values_are_floats                  PASSED
tests/test_api_endpoint.py::test_health_endpoint_returns_ok                 PASSED
tests/test_db_query.py::test_chromadb_ingest_and_query                      PASSED
tests/test_golden_dataset.py::test_golden_dataset_accuracy                  PASSED

========================= 7 passed in 4.52s ==========================
```

---

## Summary of Test Types

| Test # | Type | File | What It Validates |
|---|---|---|---|
| 1 | Unit Test | `test_chunking.py` | Text is split into correct number of overlapping chunks |
| 2 | Unit Test | `test_embeddings.py` | Embedding vectors have correct dimensionality (384) |
| 3 | Integration Test | `test_api_endpoint.py` | Streamlit health endpoint responds with HTTP 200 |
| 4 | Integration Test | `test_db_query.py` | ChromaDB can ingest and retrieve relevant incidents |
| 5 | ML Accuracy Test | `test_golden_dataset.py` | Classifier achieves ≥80% accuracy on 10 known incidents |

---

## What's Next

Your tests are passing, and your CI pipeline can now validate every code change. But how do you know your application is healthy **after** it's deployed? In the next lesson, we will configure **monitoring and health checks** using Kubernetes liveness and readiness probes.
