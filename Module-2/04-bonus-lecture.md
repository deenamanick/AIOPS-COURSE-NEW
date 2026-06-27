# 04 — Bonus Lecture: Mitigating AI Hallucinations in SRE

The biggest risk of using LLMs in IT Operations (AIOps) is **Hallucination** — when the AI confidently presents false information as fact. 

If an LLM hallucinates a command like `rm -rf /var/log/*` as a solution to a disk space issue, an inexperienced engineer might run it and delete critical audit trails.

## Techniques for Ops Prompts

In our `llm_engine.py`, we used several techniques to mitigate this risk.

### 1. Grounding with RAG
By providing `Historical Context` retrieved from ChromaDB, we ground the LLM in our actual organizational data. We aren't asking the LLM "How do I fix a database?", we are asking "How did *we* fix this database last time?"

### 2. Strict System Constraints
Look at our system prompt:
```text
CRITICAL RULE: You must base your RCA strictly on the historical context provided. 
If the historical context does not seem relevant to the new incident, state that clearly and do not hallucinate a fix.
```
By giving the LLM an explicit "escape hatch" ("state that clearly"), we reduce the chance of it guessing when it doesn't know the answer.

### 3. Temperature Control
```python
temperature=0.2
```
Temperature ranges from `0.0` to `1.0`. A high temperature (e.g., 0.8) makes the LLM more creative (great for writing poetry). A low temperature (e.g., 0.2) makes it deterministic and focused (required for engineering).

## Advanced: Few-Shot Prompting
If you find your LLM is still returning poorly formatted data, you can use **Few-Shot Prompting**. This involves giving the LLM an example of a perfect response inside the prompt itself.

Example:
```text
Here is an example of how I want you to respond:
---
**Probable Root Cause**: The Redis Cache was too small, leading to high eviction rates.
**Suggested Remediation**: Scale the Redis instance from 2GB to 4GB memory limit.
**Confidence Level**: High
---

Now, analyze the following new incident...
```

By showing the LLM exactly what a good response looks like, it is highly likely to mimic that exact structure and tone.

## Conclusion
You have successfully built a semantic RAG pipeline for AIOps! You can now generate data, embed it, search it by meaning, and have an LLM summarize the findings into actionable engineering reports.
