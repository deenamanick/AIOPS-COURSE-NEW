# Module 2: Advanced AIOps — Vector Search & LLM Root Cause Analysis

Welcome to Module 2! In this module, we transition from simple keyword matching to **Semantic Vector Search** and **Automated Generative AI Analysis**. 

## Learning Objectives
By the end of this module, you will be able to:
1. Understand the difference between Lexical (keyword) and Semantic (vector) search.
2. Initialize and query a **ChromaDB** vector database.
3. Integrate the **OpenAI API** into an IT workflow.
4. Generate automated Root Cause Analysis (RCA) reports by combining historical context with generative AI (RAG).

## Lab Environment
In this module, you will be writing Python scripts in the `lab/` folder. We have prepared an empty canvas for you to build the AIOps pipeline step-by-step.

> **Note:** You do not need to be a Python expert. We will provide the exact scripts for you to copy, paste, and run. 

### How to Set Up the Lab

Before starting Lesson 01, you must configure your Python environment.

1. **Navigate to the lab directory:**
   ```bash
   cd lab
   ```

2. **(Optional but recommended) Create a Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set your OpenAI API Key:**
   Create a file named `.env` in the `lab/` folder and add:
   ```text
   OPENAI_API_KEY=sk-your-openai-api-key-here
   ```

Once your environment is set up, you are ready to begin!

## Files in this Module
- `01-deep-dive-embeddings.md`: The theory behind Vector Embeddings.
- `02-openai-llm-rca.md`: The primary lab where you build the LLM integration.
- `03-break-fix.md`: The Break/Fix activity to test your new pipeline.
- `04-bonus-lecture.md`: Advanced topic on mitigating AI Hallucinations in Ops.

Let's get started with **01-deep-dive-embeddings.md**!
