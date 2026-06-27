import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables (like OPENAI_API_KEY) from .env file
load_dotenv()

# Initialize the OpenAI client
# It will automatically look for the OPENAI_API_KEY environment variable
client = OpenAI()

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
    system_prompt = """
    You are an expert Site Reliability Engineer (SRE) Assistant. 
    Your job is to analyze new IT incidents and provide a Root Cause Analysis (RCA) and Remediation Plan.
    You will be provided with 'Historical Context' of similar past incidents.
    
    CRITICAL RULE: You must base your RCA strictly on the historical context provided. 
    If the historical context does not seem relevant to the new incident, state that clearly and do not hallucinate a fix.
    """
    
    # 3. Build the User Prompt (The Data)
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
    
    # 4. Call the OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # You can use gpt-4o as well
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2, # Low temperature for more deterministic/factual output
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error connecting to LLM: {str(e)}"
