# Module 11: Local LLMs for AIOps & Capstone

Welcome to Module 11 — the final module of the AIOps course. In Modules 1–10, you built every layer of the AIOps stack: telemetry, anomaly detection, log analytics, incident correlation, capacity forecasting, and auto-remediation. This module adds the last capability: **AI-generated incident analysis using a local Large Language Model (LLM)** — no cloud API, no data leaving your network.

The module closes with a **full capstone**: you inject a real failure, and you must use every tool from Modules 1–10 to detect, diagnose, remediate, and document it. The LLM generates the Root Cause Analysis (RCA) report. You write the blameless post-mortem.

---

## Learning Objectives

By the end of this module, you will be able to:

1. Install **Ollama** and run a local LLM (`llama3.2:3b` or `mistral:7b`) without any cloud API.
2. Feed structured incident data to the LLM and generate a **Root Cause Analysis report**.
3. Write a **blameless post-mortem** following the industry-standard template used by Google, Netflix, and Spotify.
4. Map your organisation's AIOps maturity across the four-level model: Reactive → Proactive → Predictive → Autonomous.
5. Execute the **capstone incident lifecycle** end-to-end, integrating all tools from Modules 1–10.

---

## Prerequisites

- ✅ Modules 1–10 completed
- ✅ Python 3.10+ with `pip` available
- ✅ Docker Engine and Docker Compose v2 installed
- ✅ At least 8 GB RAM (for running the `llama3.2:3b` model)
- ✅ `curl` and `jq` installed
- ✅ Ollama installed (installation covered in Lesson 01)

---

## Lab Architecture

```text
Incident Data (alerts + logs + anomaly scores)
        │
        ▼
  Prompt Builder ──► Ollama (local LLM)
  (scripts/build_prompt.py)       │
                                  ▼
                         RCA Report (Markdown)
                                  │
                         ┌────────┴─────────┐
                         ▼                  ▼
               Post-Mortem Template    Action Items

Capstone Pipeline:
  dd (disk fill) → Anomaly (Module 5) → Alert (Module 7)
       → Correlation (Module 8) → Forecast (Module 9)
       → LLM RCA (Module 11) → Ansible cleanup (Module 10)
       → Verify → Post-Mortem
```

---

## Lab Setup

```bash
cd Module-11/lab
pip install -r requirements.txt

# Install Ollama (once)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model (3 GB download, one time)
ollama pull llama3.2:3b

# Start the lab app
docker compose up -d --build
```

Open:

- Lab app metrics: `http://localhost:5002`
- Ollama API: `http://localhost:11434`
- RCA reports: `lab/output/` (generated files)

---

## Lessons in this Module

| # | Lesson | What You'll Do |
|---|---|---|
| 01 | [Local LLMs & Ollama](./01-local-llms-ollama.md) | Install Ollama, pull a model, test it on infrastructure questions |
| 02 | [LLM Incident Report Lab](./02-llm-incident-report.md) | Feed correlated alerts and logs to the LLM; generate a structured RCA |
| 03 | [Blameless Post-Mortems](./03-post-mortem.md) | Write a post-mortem using the industry-standard template |
| 04 | [AIOps Maturity Model](./04-aiops-maturity.md) | Assess maturity level and plan the path to autonomous operations |
| 05 | [Capstone: Full Incident Lifecycle](./05-capstone.md) | Inject failure → detect → diagnose → remediate → document |
| 06 | [Course Wrap-Up & Deliverables](./06-wrap-up.md) | Final deliverables, course summary, and next steps |

Start with **01-local-llms-ollama.md**.
