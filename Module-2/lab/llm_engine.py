"""
AIOps Lab — LLM Engine
This script handles communication with OpenAI. It takes the context we found in 
ChromaDB (the historical incidents) and asks the AI to analyze the new incident based on that history.
"""

import os

# 'OpenAI' is the official library to communicate with OpenAI's API.
from openai import OpenAI

# 'load_dotenv' reads secret variables (like API keys) from a hidden file called '.env'
# so we don't have to put passwords directly into our code.
from dotenv import load_dotenv

# Load the environment variables from the .env file.
load_dotenv()

# Initialize the OpenAI client.
# The client automatically looks for an environment variable named 'OPENAI_API_KEY'.
client = OpenAI()

def generate_rca(current_incident: str, historical_context: list) -> str:
    """
    Takes the current incident description and a list of similar historical incidents.
    Constructs a detailed instruction (prompt) and asks the LLM to generate a Root Cause Analysis.
    """
    
    # 1. Format the historical context into a readable string for the AI.
    # We loop through the list of past incidents and glue them together into one large block of text.
    context_str = ""
    for idx, incident in enumerate(historical_context):
        context_str += f"\n--- Historical Incident {idx+1} ---"
        context_str += f"\nDescription: {incident['description']}"
        context_str += f"\nRoot Cause: {incident['root_cause']}"
        context_str += f"\nResolution: {incident['resolution']}\n"
        
    # 2. Build the System Prompt (The Persona and Rules)
    # The system prompt tells the AI "who" it is and sets strict rules.
    # Notice how we explicitly tell it NOT to hallucinate if the history isn't relevant.
    system_prompt = """
    You are an expert Site Reliability Engineer (SRE) Assistant. 
    Your job is to analyze new IT incidents and provide a Root Cause Analysis (RCA) and Remediation Plan.
    You will be provided with 'Historical Context' of similar past incidents.
    
    CRITICAL RULE: You must base your RCA strictly on the historical context provided. 
    If the historical context does not seem relevant to the new incident, state that clearly and do not hallucinate a fix.
    """
    
    # 3. Build the User Prompt (The Data)
    # This is the actual question/data we are sending right now.
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
        # We use the 'chat.completions' feature, which is the standard way to talk to ChatGPT models.
        response = client.chat.completions.create(
            # We specify which AI model to use. gpt-3.5-turbo is fast and cheap, but gpt-4o is smarter.
            model="gpt-3.5-turbo", 
            messages=[
                # We send both the system rules and the user data together.
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            # 'temperature' controls creativity. 0.0 is very robotic/strict. 1.0 is highly creative.
            # 0.2 means we want the AI to be very factual and stick to the prompt.
            temperature=0.2, 
        )
        
        # The API sends back a large object. We navigate through it to grab just the text content.
        return response.choices[0].message.content
        
    except Exception as e:
        # If something goes wrong (like a bad API key or no internet), catch the error so the app doesn't crash.
        return f"Error connecting to LLM: {str(e)}"
