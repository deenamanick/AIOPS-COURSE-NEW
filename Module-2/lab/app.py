"""
AIOps Lab — Streamlit Assistant Application
This file creates the visual web interface (using Streamlit). 
It connects the vector database (ChromaDB) to the AI engine (OpenAI) to provide 
an AIOps Root Cause Analysis tool.
"""

# 'streamlit' (st) is a fast way to build web apps in Python without writing HTML/CSS.
import streamlit as st

# 'csv' helps us read the incidents.csv file.
import csv

# 'os' allows us to interact with the operating system, like setting environment variables.
import os

# We try to import 'chromadb', which is our Vector Database. 
# We use a try/except block just in case the user hasn't installed it yet, 
# so the app doesn't immediately crash.
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    
# Import the function we wrote in our other file (llm_engine.py) to talk to OpenAI.
from llm_engine import generate_rca

# ==========================================
# 1. Vector Search Engine Functions
# ==========================================
def load_and_embed(csv_path: str = "incidents.csv"):
    """
    Reads the historical incidents from the CSV file and loads them into ChromaDB.
    ChromaDB automatically turns the text into mathematical vectors (embeddings)
    so we can perform 'semantic search' later.
    """
    if not CHROMA_AVAILABLE:
        st.error("chromadb not installed.")
        return None

    # 'EphemeralClient' means the database exists only in memory (RAM). 
    # If we restart the app, it resets. Perfect for a lab environment.
    client = chromadb.EphemeralClient()
    
    # A 'collection' in Chroma is like a table in a normal database.
    collection = client.create_collection(name="incidents")
    
    incidents = []
    # Check if the file actually exists before trying to open it.
    if not os.path.exists(csv_path):
        st.warning(f"{csv_path} not found. Did you run generate_incidents.py?")
        return collection
        
    # Read the CSV row by row and add it to our Python list 'incidents'.
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            incidents.append(row)

    if not incidents:
        return collection

    # Feed the data into ChromaDB.
    # Chroma needs:
    # 1. The actual text documents to embed (the descriptions)
    # 2. Metadatas (extra info we want to retrieve later, like the fix)
    # 3. Unique IDs for every record.
    collection.add(
        documents=[inc["description"] for inc in incidents],
        metadatas=[{
            "severity": inc["severity"],
            "service": inc["service"],
            "root_cause": inc["root_cause"],
            "resolution": inc["resolution"],
        } for inc in incidents],
        ids=[inc["id"] for inc in incidents],
    )
    return collection

def search_chroma(query: str, collection, top_k: int = 3):
    """
    Takes a new incident alert, turns it into a vector, and asks ChromaDB to find 
    the 'top_k' most mathematically similar historical incidents.
    """
    if not collection or collection.count() == 0:
        return []
        
    # Ask the database for the closest matches (n_results=top_k)
    results = collection.query(query_texts=[query], n_results=top_k)
    
    hits = []
    # If we got results back, we format them nicely into a list of dictionaries.
    if results["ids"] and len(results["ids"][0]) > 0:
        for i in range(len(results["ids"][0])):
            hits.append({
                "id": results["ids"][0][i],
                "description": results["documents"][0][i],
                "root_cause": results["metadatas"][0][i]["root_cause"],
                "resolution": results["metadatas"][0][i]["resolution"],
                # 'distance' tells us how similar they are. Closer to 0 = more similar.
                "distance": round(results["distances"][0][i], 4),
            })
    return hits

# ==========================================
# 2. Streamlit UI
# ==========================================

# Configure the visual appearance of the web page.
st.set_page_config(page_title="AIOps Assistant", layout="wide")
st.title("AIOps Assistant: Vector Search & LLM RCA")

# 'st.session_state' is Streamlit's way of remembering things between page clicks.
# If we don't do this, Streamlit will try to reload the entire database every time we click a button!
if "collection" not in st.session_state:
    # Show a spinning loading wheel while the database loads
    with st.spinner("Initializing ChromaDB and embedding incidents..."):
        st.session_state.collection = load_and_embed()

# Create a sidebar for settings.
st.sidebar.header("Settings")
# Let the user choose how many past incidents to look up (between 1 and 5).
top_k = st.sidebar.slider("Historical Context Matches", min_value=1, max_value=5, value=3)
# Let the user paste an API key securely in the UI.
api_key = st.sidebar.text_input("OpenAI API Key (Optional if in .env)", type="password")

# If the user pasted a key, save it to the operating system environment so OpenAI can find it.
if api_key:
    os.environ["OPENAI_API_KEY"] = api_key

st.markdown("### Enter New Incident Alert")
# A big text box for the user to paste the current broken alert.
query = st.text_area("Log message or alert description:", 
                     value="URGENT: API latency spiking on payment-gateway. Out of memory errors detected.")

# When the user clicks the "Analyze Incident" button:
if st.button("Analyze Incident"):
    if not query:
        st.warning("Please enter an incident description.")
    else:
        # ---- Step 1: Semantic Search ----
        st.subheader("1. Retrieving Historical Context (ChromaDB)")
        with st.spinner("Searching vector database..."):
            # Call our search function
            hits = search_chroma(query, st.session_state.collection, top_k)
            
        if not hits:
            st.info("No historical incidents found.")
        else:
            # Display the matched past incidents using an expander (dropdown menu)
            for hit in hits:
                with st.expander(f"Match: {hit['id']} (Distance: {hit['distance']})"):
                    st.write(f"**Desc:** {hit['description']}")
                    st.write(f"**Root Cause:** {hit['root_cause']}")
                    st.write(f"**Resolution:** {hit['resolution']}")
        
        # ---- Step 2: LLM RCA Generation ----
        st.subheader("2. Generating AI Root Cause Analysis (OpenAI)")
        # Check if we have permission to talk to OpenAI
        if not os.environ.get("OPENAI_API_KEY"):
            st.error("Please provide an OpenAI API Key in the sidebar or .env file to generate the RCA.")
        else:
            # Show a spinner, and run the function we imported from llm_engine.py
            with st.spinner("LLM is analyzing the incident..."):
                rca_report = generate_rca(query, hits)
                # Print the final AI report to the screen!
                st.markdown(rca_report)
