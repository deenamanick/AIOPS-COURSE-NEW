# 03 — Break / Fix Activity: Semantic Testing

Now that your AIOps Assistant is running, we need to test how well it performs under real-world conditions.

## The Goal
Prove that **Semantic Vector Search** works better than **Keyword Search**. We will inject an error message that uses completely different words than our historical data, but has the exact same *meaning*.

## Step 1: The Historical Data
Our `incidents.csv` (generated in Lesson 01) contains an incident like this:
*   **Description:** "High CPU utilization on billing-api due to heavy garbage collection."
*   **Root Cause:** "Memory leak in Java microservice."

## Step 2: The New Incident (The Test)
Imagine a monitoring tool throws a brand new alert. 

In your running Streamlit app (`http://localhost:8501`), type the following into the incident box:

> **"The billing server processor is pegged at 99% and it looks like the JVM is struggling to clear memory objects."**

## Step 3: Analyze the Results

Click **Analyze Incident**.

### Vector Search Results
Did it find the "High CPU utilization" incident? 
Even though you didn't use the words "CPU", "utilization", or "garbage collection", ChromaDB knows that "processor pegged at 99%" means "High CPU", and "JVM struggling to clear objects" means "garbage collection".

This is the power of Embeddings!

### LLM RCA Results
Look at the generative output from the LLM. 
1. Did it correctly identify the probable Root Cause as a memory leak?
2. Did it offer the correct remediation (Restarting pods)?
3. What is its Confidence Level?

## Step 4: The Hallucination Test

Now, try searching for something completely unrelated to IT Ops.
Type:
> **"How do I bake a chocolate cake?"**

Click Analyze.

Look at the LLM's response. Because of our `CRITICAL RULE` in the system prompt (from `llm_engine.py`), the SRE assistant should refuse to answer or state that there is no relevant historical context, rather than giving you a recipe. 

In the next Bonus lecture, we will dive deeper into controlling LLMs.
