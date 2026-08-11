# 01 — Local LLMs & Ollama

Every LLM lab in this course until now used a cloud API — OpenAI, Anthropic, or Google. Cloud APIs are convenient, but they have three problems in production operations contexts: cost at scale, data privacy (your alert payloads and logs leave your network), and network dependency (the API is unavailable when your network is degraded — exactly when you need it most).

**Ollama** solves all three. It is a local model server that runs open-weight LLMs entirely on your own machine, with a REST API that mirrors the OpenAI interface. Your incident data never leaves the host.

---

## What is Ollama?

Ollama is a tool that:

1. Downloads and manages quantized (compressed) LLM model files
2. Exposes a local HTTP API at `http://localhost:11434`
3. Handles GPU acceleration automatically (NVIDIA, AMD, Apple Silicon)
4. Supports dozens of open-weight models: Llama 3, Mistral, Phi-3, Gemma, and more

The API is compatible with the OpenAI SDK — any code that calls OpenAI can be redirected to Ollama by changing one URL.

---

## Model Comparison

| Model | Size | RAM Needed | Best For |
|---|---|---|---|
| `llama3.2:3b` | 2 GB | 4 GB | Fast responses, lab use, low-memory machines |
| `mistral:7b` | 4 GB | 8 GB | Better reasoning, more detailed outputs |
| `llama3.1:8b` | 5 GB | 10 GB | Strong general capability |
| `phi3:mini` | 2 GB | 4 GB | Very fast, Microsoft-tuned reasoning |

For this course, **`llama3.2:3b`** is the default. It runs comfortably on a machine with 8 GB RAM and produces useful incident reports. If you have 16 GB RAM, use `mistral:7b` for noticeably better output quality.

---

## Step 1: Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Verify the installation:

```bash
ollama --version
# ollama version 0.3.x
```

Start the Ollama server (it starts automatically after install; manually if needed):

```bash
ollama serve &
```

---

## Step 2: Pull a Model

```bash
# Lightweight (2 GB, ~4 GB RAM)
ollama pull llama3.2:3b

# Better quality (4 GB, ~8 GB RAM)
ollama pull mistral:7b
```

The pull downloads a quantized `.gguf` model file. It only happens once — subsequent runs use the cached model.

Verify the model is available:

```bash
ollama list
```

```text
NAME             ID              SIZE    MODIFIED
llama3.2:3b      a80c4f17acd5    2.0 GB  5 minutes ago
```

---

## Step 3: Test the Model

Run a quick interactive test:

```bash
ollama run llama3.2:3b
```

Then type:

```
Explain why a database connection pool might get exhausted. Give 3 causes and one fix for each.
```

Expected response (summarised):

```text
Database connection pool exhaustion occurs when all connections in the pool
are in use and new requests cannot be served. Three common causes:

1. Connection leaks — code acquires a connection but never releases it.
   Fix: Use context managers (with db.connect() as conn:) to guarantee release.

2. Long-running queries — slow queries hold connections open for extended periods.
   Fix: Set query timeouts and optimise the slowest queries with EXPLAIN ANALYZE.

3. Traffic spikes — a sudden load increase exhausts a pool sized for normal traffic.
   Fix: Increase pool max_size and add a queue with a timeout to shed excess load.
```

Press `Ctrl+D` or type `/bye` to exit.

---

## Step 4: Use the REST API

Ollama exposes an HTTP API that works exactly like the OpenAI API:

```bash
curl http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "prompt": "What is the most common cause of a MySQL deadlock?",
    "stream": false
  }' | python3 -m json.tool
```

```json
{
  "model": "llama3.2:3b",
  "response": "A MySQL deadlock most commonly occurs when two or more transactions...",
  "done": true,
  "total_duration": 3821450000,
  "prompt_eval_count": 18,
  "eval_count": 142
}
```

The `stream: false` option waits for the full response before returning. Use `stream: true` for real-time token streaming.

---

## Step 5: Python Client

The lab uses `requests` directly, but you can also use the `openai` Python SDK:

```python
from openai import OpenAI

# Point the OpenAI client at Ollama
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Ollama does not require a real API key
)

response = client.chat.completions.create(
    model="llama3.2:3b",
    messages=[
        {"role": "system", "content": "You are an expert SRE."},
        {"role": "user", "content": "What causes connection pool exhaustion?"},
    ],
)
print(response.choices[0].message.content)
```

This is identical to calling OpenAI GPT-4 — only the `base_url` and `api_key` change.

---

## LLM Risks in Operations

Before using an LLM to generate remediation actions, understand the failure modes:

| Risk | Description | Mitigation |
|---|---|---|
| **Hallucination** | The model states incorrect facts with confidence | Always verify LLM output against actual metrics before acting |
| **Unsafe remediation** | LLM may suggest deleting files, restarting databases, scaling down | LLM output is read-only advice; humans or validated playbooks execute |
| **Prompt injection** | Log lines may contain text that manipulates the LLM | Sanitize and quote log input; do not execute LLM-suggested shell commands directly |
| **Outdated knowledge** | Open-weight models have a training cutoff | Verify version-specific advice against current documentation |
| **Overconfidence** | LLM may sound authoritative when guessing | Use LLM for *hypotheses*, not *conclusions* |

**The golden rule for LLMs in AIOps: the LLM generates hypotheses; engineers and validated automation execute actions.**

---

## Cloud API vs Local Comparison

| Dimension | Cloud API (OpenAI GPT-4) | Local (Ollama llama3.2:3b) |
|---|---|---|
| Response quality | Higher (larger model) | Good (sufficient for RCA) |
| Latency | 2–8 seconds | 1–5 seconds on modern CPU |
| Cost | $0.01–0.03 per 1K tokens | $0 (electricity only) |
| Data privacy | Data sent to OpenAI servers | Data never leaves your host |
| Availability | Requires internet | Works offline, in air-gapped envs |
| Setup | API key only | `ollama pull llama3.2:3b` |

For incident response in production, local is often preferable: you need the AI available *exactly when the network is stressed*.

---

## Validation Checklist

- [ ] Ollama installed and `ollama --version` returns a version number.
- [ ] `llama3.2:3b` (or `mistral:7b`) pulled and visible in `ollama list`.
- [ ] Interactive test answered the connection pool question correctly.
- [ ] REST API returned a JSON response from `curl`.
- [ ] Python client connected to Ollama via the OpenAI-compatible endpoint.
- [ ] LLM risks identified and mitigation strategy understood.
