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

Since we built a lab environment in Module 1, you will run this lab inside your `aiops-control` Virtual Machine.

1. **SSH into your VM:**
   ```bash
   vagrant ssh aiops-control
   ```

2. **Navigate to the Module 2 lab directory:**
   (Assuming you have copied or cloned this repository into `/opt/AIOPS-COURSE-NEW`)
   ```bash
   cd /opt/AIOPS-COURSE-NEW/Module-2/lab
   ```

3. **Create a Virtual Environment (to keep the VM clean):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set your OpenAI API Key:**
   Create a file named `.env` in the `lab/` folder and add:
   ```text
   OPENAI_API_KEY=sk-your-openai-api-key-here
   ```

6. **Start the Application:**
   Because you are inside a VM, you must tell Streamlit to listen on all interfaces so your host browser can reach it.
   ```bash
   streamlit run app.py --server.address 0.0.0.0
   ```

Once your environment is set up and running, you can access the UI at **http://localhost:8501** on your host machine and begin the lessons!

## Files in this Module
- `01-deep-dive-embeddings.md`: The theory behind Vector Embeddings.
- `02-openai-llm-rca.md`: The primary lab where you build the LLM integration.
- `03-break-fix.md`: The Break/Fix activity to test your new pipeline.
- `04-bonus-lecture.md`: Advanced topic on mitigating AI Hallucinations in Ops.

Let's get started with **01-deep-dive-embeddings.md**!
