# 'os' allows us to read environment variables (like passwords or API keys) from the computer.
import os
# Groq provides a free, ultra-fast API for open-source LLMs like Llama 3.
# The Groq SDK is OpenAI-compatible, so the code structure is nearly identical.
from groq import Groq
# 'load_dotenv' helps us read secrets from a local .env file.
from dotenv import load_dotenv

# Load environment variables (like GROQ_API_KEY) from .env file
load_dotenv()

# Initialize the Groq client
# It will automatically look for the GROQ_API_KEY environment variable
client = Groq()

def generate_rca(current_incident: str, historical_context: list) -> str:
    """
    Takes the current incident description and a list of historical incidents (from ChromaDB).
    Constructs a prompt and asks the LLM to generate a Root Cause Analysis.
    """
    
    # 1. Format the historical context into a readable string for the LLM
    context_str = ""
    for idx, incident in enumerate(historical_context):
        context_str += f"\n--- Historical Incident {idx+1} ---"
        context_str += f"\nDescription: {incident['description']}"
        context_str += f"\nRoot Cause: {incident['root_cause']}"
        context_str += f"\nResolution: {incident['resolution']}\n"
        
    # 2. Build the System Prompt (The Persona and Rules)
    # The system prompt tells the AI how it should behave and set its identity.
    system_prompt = """
    You are an expert Site Reliability Engineer (SRE) Assistant. 
    Your job is to analyze new IT incidents and provide a Root Cause Analysis (RCA) and Remediation Plan.
    You will be provided with 'Historical Context' of similar past incidents.
    
    CRITICAL RULE: You must base your RCA strictly on the historical context provided. 
    If the historical context does not seem relevant to the new incident, state that clearly and do not hallucinate a fix.
    """
    
    # 3. Build the User Prompt (The Data)
    # This is the actual question/data we are passing to the AI for this specific run.
    user_prompt = f"""
    Please analyze this new incident:
    "{current_incident}"
    
    Here are similar past incidents for context:
    {context_str}
    
    Format your response with the following headers:
    1. **Probable Root Cause**
    2. **Suggested Remediation**
    3. **Confidence Level** (High/Medium/Low based on how closely it matches history)
    """
    
    # 4. Call the Groq API (runs Llama 3.1 8B at ultra-low latency)
    try:
        response = client.chat.completions.create(
            # Llama 3.1 8B is free on Groq and runs at ~500 tokens/second
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            # Temperature controls creativity. 
            # 0.2 is low, meaning the AI will be more factual and deterministic.
            temperature=0.2, 
        )
        
        # Extract the actual text response from the API result
        return response.choices[0].message.content
        
    except Exception as e:
        # If something goes wrong (like a bad API key), return the error message nicely
        return f"Error connecting to LLM: {str(e)}"
