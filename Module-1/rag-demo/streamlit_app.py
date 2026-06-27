"""
AIOps Incident Assistant — Streamlit UI
Interactive RAG-powered assistant that finds similar past incidents.
Supports both Jaccard (default) and ChromaDB (bonus) search engines.
"""
import os
import streamlit as st
import pandas as pd
from rag_engine import load_incidents, search

# Try importing ChromaDB engine (bonus)
try:
    from chroma_engine import load_and_embed, search_chroma
    CHROMA_AVAILABLE = True
except Exception:
    CHROMA_AVAILABLE = False

# --- Page Config ---
st.set_page_config(
    page_title="AIOps Incident Assistant",
    page_icon="🔍",
    layout="wide",
)

# --- Styling ---
st.markdown("""
<style>
    .severity-critical { color: #ff4444; font-weight: bold; }
    .severity-high { color: #ff8800; font-weight: bold; }
    .severity-medium { color: #ffcc00; font-weight: bold; }
    .stMetric { background-color: #1e1e2e; border-radius: 8px; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.title("🔍 AIOps Incident Assistant")
st.markdown("*Find similar past incidents using RAG (Retrieval-Augmented Generation)*")
st.divider()

# --- Load Data ---
@st.cache_data
def get_incidents():
    return load_incidents("incidents.csv")

incidents = get_incidents()
st.sidebar.metric("📊 Incidents Loaded", len(incidents))

# --- Engine Selection ---
engine = st.sidebar.radio(
    "Search Engine",
    ["Jaccard (Keyword)", "ChromaDB (Vector)"] if CHROMA_AVAILABLE else ["Jaccard (Keyword)"],
    help="Jaccard uses keyword overlap. ChromaDB uses semantic vector similarity."
)

top_k = st.sidebar.slider("Results to show", 1, 10, 3)

# --- ChromaDB Collection (lazy load) ---
chroma_collection = None
if engine == "ChromaDB (Vector)" and CHROMA_AVAILABLE:
    with st.spinner("Loading ChromaDB embeddings..."):
        try:
            chroma_host = os.getenv("CHROMA_HOST", "chromadb")
            chroma_collection = load_and_embed("incidents.csv", chroma_host=chroma_host)
        except Exception as e:
            st.error(f"ChromaDB connection failed: {e}")
            st.info("Make sure ChromaDB is running. Falling back to Jaccard.")
            engine = "Jaccard (Keyword)"

# --- Search ---
st.subheader("🔎 Search Past Incidents")
query = st.text_input(
    "Describe the current issue:",
    placeholder="e.g., database connection pool exhausted, nginx 502 error, disk space full..."
)

if query:
    with st.spinner("Searching..."):
        if engine == "ChromaDB (Vector)" and chroma_collection:
            results = search_chroma(query, chroma_collection, top_k=top_k)
        else:
            results = search(query, incidents, top_k=top_k)

    if not results:
        st.warning("No matching incidents found. Try different keywords.")
    else:
        st.success(f"Found {len(results)} similar incidents using **{engine}**")

        for i, result in enumerate(results):
            severity = result["severity"]
            severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(severity, "⚪")

            # Score display differs by engine
            if "similarity_score" in result:
                score_label = f"Jaccard Score: {result['similarity_score']}"
            else:
                score_label = f"Distance: {result['distance']}"

            with st.expander(
                f"{severity_emoji} #{result['id']} — {result['description'][:80]}... ({score_label})",
                expanded=(i == 0)
            ):
                col1, col2, col3 = st.columns(3)
                col1.metric("Severity", severity.upper())
                col2.metric("Service", result["service"])
                col3.metric("Timestamp", result["timestamp"])

                st.markdown("**📝 Description**")
                st.write(result["description"])

                st.markdown("**🔍 Root Cause**")
                st.info(result["root_cause"])

                st.markdown("**✅ Resolution**")
                st.success(result["resolution"])

# --- Data Explorer ---
st.divider()
with st.expander("📋 View All Incidents", expanded=False):
    df = pd.DataFrame(incidents)
    df = df.drop(columns=["tokens"], errors="ignore")
    st.dataframe(df, use_container_width=True)

# --- Footer ---
st.divider()
st.caption("AIOps Course — Module 1: RAG Demo Lab | Powered by Streamlit")
