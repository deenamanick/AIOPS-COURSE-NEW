"""
AIOps Lab — Streamlit Assistant Application
This file creates the visual web interface (using Streamlit). 
It connects the vector database (ChromaDB) to the AI engine (OpenAI) to provide 
an AIOps Root Cause Analysis tool, and includes Kubernetes simulation tools.
"""

# 'streamlit' (st) is a fast way to build web apps in Python without writing HTML/CSS.
import streamlit as st
# 'csv' helps us read the incidents.csv file.
import csv
# 'os' allows us to interact with the operating system, like setting environment variables.
import os
# 'time' is used to add deliberate delays in our simulation loops.
import time

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
    """Load incidents from CSV and store embeddings in ChromaDB (Memory)."""
    if not CHROMA_AVAILABLE:
        st.error("chromadb not installed.")
        return None

    # Using EphemeralClient for lab purposes (data is cleared on restart)
    client = chromadb.EphemeralClient()
    
    # A 'collection' in Chroma is like a table in a normal database.
    collection = client.create_collection(name="incidents")
    
    incidents = []
    # Auto-generate incidents if the file doesn't exist
    if not os.path.exists(csv_path):
        try:
            from generate_incidents import generate_incidents
            generate_incidents(100)
        except Exception as e:
            st.error(f"Error auto-generating incidents: {str(e)}")
            
    # Read the CSV row by row and add it to our Python list 'incidents'.
    if os.path.exists(csv_path):
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                incidents.append(row)

    if not incidents:
        return collection

    # Feed the data into ChromaDB.
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
    """Search for similar incidents using ChromaDB vector similarity."""
    if not collection or collection.count() == 0:
        return []
        
    # Ask the database for the closest matches (n_results=top_k)
    results = collection.query(query_texts=[query], n_results=top_k)
    
    hits = []
    # Format the results into a nicely structured list of dictionaries
    if results["ids"] and len(results["ids"][0]) > 0:
        for i in range(len(results["ids"][0])):
            hits.append({
                "id": results["ids"][0][i],
                "description": results["documents"][0][i],
                "root_cause": results["metadatas"][0][i]["root_cause"],
                "resolution": results["metadatas"][0][i]["resolution"],
                "distance": round(results["distances"][0][i], 4),
            })
    return hits

# ==========================================
# 2. Streamlit UI
# ==========================================
# Configure the visual appearance of the web page.
st.set_page_config(page_title="AIOps Assistant", layout="wide")
st.title("AIOps Assistant: Vector Search & LLM RCA")

# Initialize ChromaDB once and cache it in session state
# This prevents Streamlit from reloading the database on every button click.
if "collection" not in st.session_state:
    with st.spinner("Initializing ChromaDB and embedding incidents..."):
        st.session_state.collection = load_and_embed()

# Create a sidebar for settings.
st.sidebar.header("Settings")
# Let the user choose how many past incidents to look up (between 1 and 5).
top_k = st.sidebar.slider("Historical Context Matches", min_value=1, max_value=5, value=3)
# Let the user paste an API key securely in the UI.
api_key = st.sidebar.text_input("OpenAI API Key (Optional if in .env/Secret)", type="password")

if api_key:
    # Save it to the operating system environment so OpenAI can find it.
    os.environ["OPENAI_API_KEY"] = api_key

# Kubernetes Lab Tools - Extra feature for Module 3
st.sidebar.markdown("---")
st.sidebar.subheader("SRE Kubernetes Lab Tools")
st.sidebar.markdown("Use this to test Kubernetes memory limit enforcement and watch self-healing in action.")

# When the user clicks the OOM button, we intentionally crash the app by eating up RAM!
if st.sidebar.button("Trigger Out-of-Memory (OOM)", type="primary"):
    st.sidebar.warning("Allocating memory rapidly to trigger Kubernetes OOM-Kill...")
    
    # Visual cues in main panel
    st.warning("🚨 INGESTION SIMULATED: Consuming system RAM to bypass the 512Mi limit...")
    
    time.sleep(0.5)
    
    # Loop and allocate huge memory chunks to force Kubernetes to kill the pod.
    memory_chunks = []
    chunk_count = 0
    while True:
        chunk_count += 1
        # Allocate 50MB of bytes
        memory_chunks.append(b"x" * (1024 * 1024 * 50))
        st.write(f"Allocated {chunk_count * 50} MB of RAM...")
        time.sleep(0.05)  # Yield slightly so the UI can update

st.markdown("### Enter New Incident Alert")
# A big text box for the user to paste the current broken alert.
query = st.text_area("Log message or alert description:", 
                     value="URGENT: API latency spiking on payment-gateway. Out of memory errors detected.")

# When the user clicks the "Analyze Incident" button:
if st.button("Analyze Incident"):
    if not query:
        st.warning("Please enter an incident description.")
    else:
        # Step 1: Semantic Search
        st.subheader("1. Retrieving Historical Context (ChromaDB)")
        with st.spinner("Searching vector database..."):
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
        
        # Step 2: LLM RCA Generation
        st.subheader("2. Generating AI Root Cause Analysis (OpenAI)")
        # Check if we have permission to talk to OpenAI (either locally or via K8s Secret)
        if not os.environ.get("OPENAI_API_KEY"):
            st.error("Please provide an OpenAI API Key in the sidebar or via K8s Secret (OPENAI_API_KEY env var).")
        else:
            # Run the function we imported from llm_engine.py
            with st.spinner("LLM is analyzing the incident..."):
                rca_report = generate_rca(query, hits)
                st.markdown(rca_report)
