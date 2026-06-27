# Module 2: Advanced AIOps — Vector Search & LLM Root Cause Analysis

Welcome to Module 2! In Module 1, you built a local lab, deployed a RAG demo, and previewed ChromaDB. Now we go deeper — you will containerize an upgraded AI assistant, replace keyword matching with semantic vector search, and integrate the **OpenAI API** to automatically generate Root Cause Analysis reports.

## Learning Objectives

By the end of this module, you will be able to:
1. Explain the difference between Lexical (keyword) and Semantic (vector) search with concrete examples.
2. Write a Dockerfile and docker-compose for an AI/ML application.
3. Initialize and query a **ChromaDB** vector database with real incident data.
4. Integrate the **OpenAI API** into an IT operations workflow.
5. Generate automated Root Cause Analysis (RCA) reports using RAG (Retrieval-Augmented Generation).
6. Estimate API costs and understand production trade-offs.

## Prerequisites

- ✅ Module 1 completed (your `aiops-control` VM should be running)
- ✅ Docker and Docker Compose installed on `aiops-control` (done in Module 1)
- ✅ An OpenAI API key ([platform.openai.com](https://platform.openai.com))

> **Note:** You do not need to be a Python expert. All scripts are provided as copy-paste blocks. The focus is on understanding the AIOps concepts, not writing code from scratch.

---

## How to Set Up the Lab

You will run this lab inside your `aiops-control` Virtual Machine from Module 1.

### Step 1: SSH into your VM
```bash
vagrant ssh aiops-control
```

### Step 2: Copy Module 2 lab files to the VM
```bash
# From your host machine (not inside the VM)
cd Module-2
vagrant ssh-config aiops-control > /tmp/ssh-config-control
scp -r -F /tmp/ssh-config-control lab/* aiops-control:/opt/module2-lab/
```

### Step 3: Build and run the Docker container
```bash
vagrant ssh aiops-control
cd /opt/module2-lab

# Generate the incident data first
python3 generate_incidents.py

# Build and start the containerized assistant
docker compose up -d --build
```

### Step 4: Set your OpenAI API Key
Create a `.env` file in `/opt/module2-lab/`:
```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
docker compose restart
```

### Step 5: Access the UI
Open **http://localhost:8501** in your host browser.

---

## Lessons in this Module

| # | Lesson | What You'll Do |
|---|---|---|
| 01 | [Deep Dive: Embeddings](./01-deep-dive-embeddings.md) | Understand how text becomes vectors and why it matters |
| 02 | [Dockerize the Assistant](./02-dockerize-assistant.md) | Write a Dockerfile and docker-compose for the upgraded app |
| 03 | [ChromaDB Vector Search](./03-chromadb-vector-search.md) | Replace Jaccard with semantic search and compare results |
| 04 | [OpenAI LLM RCA](./04-openai-llm-rca.md) | Connect vector search to OpenAI for automated diagnosis |
| 05 | [Break/Fix Exercises](./05-break-fix.md) | 5 hands-on infrastructure troubleshooting exercises |
| 06 | [Cost & Performance](./06-cost-and-performance.md) | Token counting, latency benchmarks, production awareness |
| 07 | [Bonus Lecture](./07-bonus-lecture.md) | AI Hallucinations + 4 student deliverables |

Let's get started with **01-deep-dive-embeddings.md**!
