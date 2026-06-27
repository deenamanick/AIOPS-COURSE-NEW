# 06 — Cost & Performance: Production Awareness

Building an AI pipeline is step one. Running it in production requires understanding **cost**, **latency**, and **caching**. This lesson teaches you to think like an SRE managing an AI budget.

---

## Token Economics

### What Are Tokens?

Tokens are the billing unit for LLM APIs. Roughly:
- **1 token ≈ 4 characters** of English text
- **1 token ≈ ¾ of a word**
- The word "embeddings" = 3 tokens
- "ChatGPT is great" = 4 tokens

### Our Query Breakdown

For a typical RCA query, here's the token math:

| Component | Content | Estimated Tokens |
|---|---|---|
| System prompt | SRE persona + rules | ~80 tokens |
| Historical context | 3 incidents × (~70 tokens each) | ~210 tokens |
| User prompt | "Analyze this incident..." + the alert | ~50 tokens |
| **Input total** | | **~340 tokens** |
| LLM response | Root Cause + Remediation + Confidence | ~150 tokens |
| **Total per query** | | **~490 tokens** |

### Cost Comparison by Model

| Model | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) | Cost per RCA Query | Best For |
|---|---|---|---|---|
| `gpt-3.5-turbo` | $0.50 | $1.50 | ~$0.0004 | Cost-effective, good quality |
| `gpt-4o-mini` | $0.15 | $0.60 | ~$0.0001 | Budget-friendly, decent quality |
| `gpt-4o` | $2.50 | $10.00 | ~$0.002 | Highest quality, expensive |

---

## Monthly Cost Estimation

### Scenario: A Small SRE Team

| Parameter | Value |
|---|---|
| Incidents per day | 50 |
| Days per month | 30 |
| Total queries/month | 1,500 |
| Tokens per query | ~490 |
| Total tokens/month | ~735,000 |

| Model | Monthly Cost |
|---|---|
| `gpt-3.5-turbo` | **$0.59** |
| `gpt-4o-mini` | **$0.18** |
| `gpt-4o` | **$2.94** |

**Key Insight:** Even at 50 incidents/day, the API cost is under $3/month with `gpt-4o`. This is orders of magnitude cheaper than a junior SRE spending 30 minutes per manual RCA.

### Scenario: A Large Enterprise (500 incidents/day)

| Model | Monthly Cost |
|---|---|
| `gpt-3.5-turbo` | **$5.88** |
| `gpt-4o-mini` | **$1.84** |
| `gpt-4o` | **$29.40** |

Still very affordable compared to human labor!

---

## Latency Comparison

How fast is each component of the pipeline?

| Component | Typical Latency | What Affects It |
|---|---|---|
| **Generate incidents.py** | 0.1s | One-time setup |
| **ChromaDB ingestion** (100 docs) | 2-5s | Embedding model speed |
| **ChromaDB query** | 10-50ms | Number of stored vectors |
| **OpenAI API call** | 1-3s | Model size, token count, API load |
| **End-to-end (query → RCA)** | **2-4s** | Network latency to OpenAI |

### Comparison with Manual RCA

| Method | Time per Incident | Quality |
|---|---|---|
| Junior SRE (manual) | 15-30 minutes | Variable — depends on experience |
| Senior SRE (manual) | 5-10 minutes | High — but expensive salary |
| **Module 2 Pipeline** | **3-4 seconds** | **High — consistent, based on history** |

---

## Caching Strategies

In production, you don't want to call the LLM for the same incident pattern repeatedly.

### Strategy 1: Query Deduplication

If the same alert fires 10 times in 5 minutes (e.g., "API latency spiking"), you should:
1. Cache the first RCA response
2. Return the cached result for identical or near-identical queries
3. Only call the LLM again after a cooldown period (e.g., 5 minutes)

### Strategy 2: Precomputed RCA Cache

For your most common incident patterns, pre-generate RCAs:
```
"database connection pool exhausted" → Pre-cached RCA
"SSL certificate expired" → Pre-cached RCA
"disk space full" → Pre-cached RCA
```

This eliminates LLM calls entirely for known patterns.

### Strategy 3: Model Downgrade for Repeated Queries

Use `gpt-4o` for the first occurrence of a new pattern (highest quality), then downgrade to `gpt-3.5-turbo` for subsequent similar incidents (cost savings).

---

## Production Architecture Considerations

When moving from lab to production, consider these upgrades:

| Lab Setup | Production Upgrade | Why |
|---|---|---|
| `EphemeralClient()` (in-memory ChromaDB) | Persistent ChromaDB with Docker volume | Data survives container restarts |
| Single container | Kubernetes Deployment with replicas | High availability |
| `.env` file for API key | K8s Secret / Vault | Secure key management |
| No rate limiting | Token bucket rate limiter | Prevent accidental cost spikes |
| Streamlit UI | API endpoint + Dashboard | Integrate with PagerDuty, Slack, etc. |

---

## Lab: Estimate Your Own Costs

### Exercise

Based on your organization (or a hypothetical one), fill in this planning table:

| Parameter | Your Estimate |
|---|---|
| Incidents per day | _(fill in)_ |
| Working days per month | _(fill in)_ |
| Total queries per month | _(calculate)_ |
| Chosen model | _(gpt-3.5-turbo / gpt-4o-mini / gpt-4o)_ |
| Monthly API cost | _(calculate)_ |
| Current manual RCA time per incident | _(fill in)_ |
| SRE hourly cost | _(fill in)_ |
| Monthly manual RCA cost | _(calculate)_ |
| **Monthly savings with AIOps** | _(manual cost - API cost)_ |

---

## What's Next

Proceed to **07-bonus-lecture.md** for the final module activity — mitigating AI hallucinations and completing your 4 student deliverables.
