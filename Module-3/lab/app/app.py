import streamlit as st
import csv
import os
import time

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    
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
    
    collection = client.create_collection(name="incidents")
    
    incidents = []
    if not os.path.exists(csv_path):
        # Auto-generate if missing
        try:
            from generate_incidents import generate_incidents
            generate_incidents(100)
        except Exception as e:
            st.error(f"Error auto-generating incidents: {str(e)}")
            
    if os.path.exists(csv_path):
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                incidents.append(row)

    if not incidents:
        return collection

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
        
    results = collection.query(query_texts=[query], n_results=top_k)
    
    hits = []
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
st.set_page_config(page_title="AIOps Assistant", layout="wide")
st.title("AIOps Assistant: Vector Search & LLM RCA")

# Initialize ChromaDB once and cache it in session state
if "collection" not in st.session_state:
    with st.spinner("Initializing ChromaDB and embedding incidents..."):
        st.session_state.collection = load_and_embed()

st.sidebar.header("Settings")
top_k = st.sidebar.slider("Historical Context Matches", min_value=1, max_value=5, value=3)
api_key = st.sidebar.text_input("OpenAI API Key (Optional if in .env/Secret)", type="password")

if api_key:
    os.environ["OPENAI_API_KEY"] = api_key

# Kubernetes Lab Tools
st.sidebar.markdown("---")
st.sidebar.subheader("SRE Kubernetes Lab Tools")
st.sidebar.markdown("Use this to test Kubernetes memory limit enforcement and watch self-healing in action.")

if st.sidebar.button("Trigger Out-of-Memory (OOM)", type="primary"):
    st.sidebar.warning("Allocating memory rapidly to trigger Kubernetes OOM-Kill...")
    
    # Visual cues in main panel
    st.warning("🚨 INGESTION SIMULATED: Consuming system RAM to bypass the 512Mi limit...")
    
    time.sleep(0.5)
    
    # Loop and allocate huge memory chunks
    memory_chunks = []
    chunk_count = 0
    while True:
        chunk_count += 1
        # Allocate 50MB of bytes
        memory_chunks.append(b"x" * (1024 * 1024 * 50))
        st.write(f"Allocated {chunk_count * 50} MB of RAM...")
        time.sleep(0.05)  # Yield slightly

st.markdown("### Enter New Incident Alert")
query = st.text_area("Log message or alert description:", 
                     value="URGENT: API latency spiking on payment-gateway. Out of memory errors detected.")

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
            for hit in hits:
                with st.expander(f"Match: {hit['id']} (Distance: {hit['distance']})"):
                    st.write(f"**Desc:** {hit['description']}")
                    st.write(f"**Root Cause:** {hit['root_cause']}")
                    st.write(f"**Resolution:** {hit['resolution']}")
        
        # Step 2: LLM RCA Generation
        st.subheader("2. Generating AI Root Cause Analysis (OpenAI)")
        if not os.environ.get("OPENAI_API_KEY"):
            st.error("Please provide an OpenAI API Key in the sidebar or via K8s Secret (OPENAI_API_KEY env var).")
        else:
            with st.spinner("LLM is analyzing the incident..."):
                rca_report = generate_rca(query, hits)
                st.markdown(rca_report)
