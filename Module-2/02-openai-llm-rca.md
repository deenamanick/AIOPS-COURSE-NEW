# 02 — OpenAI LLM RCA Integration

In this lab, we will connect our Vector Search (ChromaDB) to an LLM (OpenAI) to automate Root Cause Analysis.

## The Retrieval-Augmented Generation (RAG) Flow

1. **User Input:** "The database is crashing with out of memory errors."
2. **Retrieval:** We search ChromaDB. It finds a similar incident from last month: "OOM killer terminated DB process." It retrieves the Root Cause and Resolution for that incident.
3. **Augmentation:** We inject those historical findings into our Prompt.
4. **Generation:** We send the prompt to OpenAI. The LLM reads the history and writes a new, formatted Root Cause Analysis tailored to the current situation.

## Prerequisites

You will need an OpenAI API key.
1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Create an API key.
3. (Optional) In your `lab/` folder, create a `.env` file and add:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

## Lab: Write the LLM Engine

We have provided the scripts for you. Create a file named `llm_engine.py` in your `lab/` folder and copy this exact code into it:

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables (like OPENAI_API_KEY) from .env file
load_dotenv()
client = OpenAI()

def generate_rca(current_incident: str, historical_context: list) -> str:
    # 1. Format the historical context into a readable string for the LLM
    context_str = ""
    for idx, incident in enumerate(historical_context):
        context_str += f"\n--- Historical Incident {idx+1} ---"
        context_str += f"\nDescription: {incident['description']}"
        context_str += f"\nRoot Cause: {incident['root_cause']}"
        context_str += f"\nResolution: {incident['resolution']}\n"
        
    # 2. Build the System Prompt
    system_prompt = """
    You are an expert Site Reliability Engineer (SRE) Assistant. 
    Your job is to analyze new IT incidents and provide a Root Cause Analysis (RCA) and Remediation Plan.
    You will be provided with 'Historical Context' of similar past incidents.
    
    CRITICAL RULE: You must base your RCA strictly on the historical context provided.
    """
    
    # 3. Build the User Prompt
    user_prompt = f"""
    Please analyze this new incident:
    "{current_incident}"
    
    Here are similar past incidents for context:
    {context_str}
    
    Format your response with the following headers:
    1. **Probable Root Cause**
    2. **Suggested Remediation**
    3. **Confidence Level**
    """
    
    # 4. Call the OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error connecting to LLM: {str(e)}"
```

### Why Temperature 0.2?
Notice `temperature=0.2`. In IT Operations, we want **facts**, not creativity. A low temperature makes the LLM more deterministic and less likely to hallucinate a false solution.

## Running the App

To tie it all together, look at `app.py`. We have already built the Streamlit interface that combines the ChromaDB vector search with this `llm_engine.py`.

Run the application (binding to 0.0.0.0 so it's accessible from your host machine):
```bash
streamlit run app.py --server.address 0.0.0.0
```

Open `http://localhost:8501` in your host browser. Enter your OpenAI API key if you didn't use a `.env` file, and test out an incident!
