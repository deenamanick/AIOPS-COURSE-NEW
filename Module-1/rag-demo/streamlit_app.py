"""
AIOps Incident Assistant — Streamlit UI
Interactive RAG-powered assistant that finds similar past incidents.
Supports both Jaccard (default) and ChromaDB (bonus) search engines.

(This script creates a visual web-based User Interface (UI) using a tool called Streamlit.)
"""
import os
import streamlit as st # Streamlit makes it incredibly easy to build web apps in Python
import pandas as pd    # Pandas is a powerful tool for working with data tables
from rag_engine import load_incidents, search # Importing functions from our own rag_engine.py file!

# Try importing the advanced AI search engine functions from our chroma_engine.py file
try:
    from chroma_engine import load_and_embed, search_chroma
    CHROMA_AVAILABLE = True
except Exception:
    # If the file or library isn't there, we just set this to False and continue
    CHROMA_AVAILABLE = False

# --- Page Config ---
# This sets up the web browser tab title, the icon, and tells the page to use the full width of the screen
st.set_page_config(
    page_title="AIOps Incident Assistant",
    page_icon="🔍",
    layout="wide",
)

# --- Styling ---
# Here we inject some custom CSS code to make things look pretty (colors for severity, etc.)
# 'unsafe_allow_html=True' tells Streamlit it's okay to run this raw HTML/CSS.
st.markdown("""
<style>
    .severity-critical { color: #ff4444; font-weight: bold; }
    .severity-high { color: #ff8800; font-weight: bold; }
    .severity-medium { color: #ffcc00; font-weight: bold; }
    .stMetric { background-color: #1e1e2e; border-radius: 8px; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
# 'st.title' displays a big heading on the webpage
st.title("🔍 AIOps Incident Assistant")
# 'st.markdown' displays regular text (with support for bold/italics)
st.markdown("*Find similar past incidents using RAG (Retrieval-Augmented Generation)*")
# 'st.divider' draws a horizontal line across the page
st.divider()

# --- Load Data ---
# '@st.cache_data' is a neat trick! It tells Streamlit to remember the loaded data in memory
# so it doesn't have to re-read the CSV file every single time the user clicks a button.
@st.cache_data
def get_incidents():
    return load_incidents("incidents.csv")

# Actually load the data using the function above
incidents = get_incidents()
# Display a little dashboard metric on the sidebar showing how many incidents we loaded
st.sidebar.metric("📊 Incidents Loaded", len(incidents))

# --- Engine Selection ---
# Create a radio button menu on the sidebar to choose the search engine
engine = st.sidebar.radio(
    "Search Engine",
    # If Chroma is available, show both options. Otherwise, only show Jaccard.
    ["Jaccard (Keyword)", "ChromaDB (Vector)"] if CHROMA_AVAILABLE else ["Jaccard (Keyword)"],
    help="Jaccard uses keyword overlap. ChromaDB uses semantic vector similarity."
)

# Add a slider to the sidebar to let the user pick how many results they want to see (1 to 10)
top_k = st.sidebar.slider("Results to show", 1, 10, 3)

# --- ChromaDB Collection (lazy load) ---
chroma_collection = None
# If the user selected ChromaDB, we need to load the AI database
if engine == "ChromaDB (Vector)" and CHROMA_AVAILABLE:
    # 'st.spinner' shows a loading wheel while the code inside it runs
    with st.spinner("Loading ChromaDB embeddings..."):
        try:
            # Look for an environment variable called CHROMA_HOST, or default to "chromadb"
            chroma_host = os.getenv("CHROMA_HOST", "chromadb")
            chroma_collection = load_and_embed("incidents.csv", chroma_host=chroma_host)
        except Exception as e:
            # If it fails, show a red error box and a blue info box, then fall back to the basic search
            st.error(f"ChromaDB connection failed: {e}")
            st.info("Make sure ChromaDB is running. Falling back to Jaccard.")
            engine = "Jaccard (Keyword)"

# --- Search ---
# Add a medium-sized heading
st.subheader("🔎 Search Past Incidents")
# Create a text box where the user can type their problem
query = st.text_input(
    "Describe the current issue:",
    placeholder="e.g., database connection pool exhausted, nginx 502 error, disk space full..."
)

# This block runs IF the user has typed something into the 'query' text box
if query:
    # Show a loading wheel
    with st.spinner("Searching..."):
        # Run the search using whichever engine is currently selected
        if engine == "ChromaDB (Vector)" and chroma_collection:
            results = search_chroma(query, chroma_collection, top_k=top_k)
        else:
            results = search(query, incidents, top_k=top_k)

    # If the search found absolutely nothing, show a yellow warning box
    if not results:
        st.warning("No matching incidents found. Try different keywords.")
    else:
        # Show a green success box with how many results were found
        st.success(f"Found {len(results)} similar incidents using **{engine}**")

        # Loop through the search results to display them on the page
        for i, result in enumerate(results):
            severity = result["severity"]
            # Pick a colored emoji based on the severity text
            severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(severity, "⚪")

            # Format the score text differently depending on which engine was used
            if "similarity_score" in result:
                score_label = f"Jaccard Score: {result['similarity_score']}"
            else:
                score_label = f"Distance: {result['distance']}"

            # Create an accordion-style drop-down box for each result
            # We make the very first result (i == 0) expanded by default
            with st.expander(
                f"{severity_emoji} #{result['id']} — {result['description'][:80]}... ({score_label})",
                expanded=(i == 0)
            ):
                # Split the display into 3 neat columns
                col1, col2, col3 = st.columns(3)
                col1.metric("Severity", severity.upper())
                col2.metric("Service", result["service"])
                col3.metric("Timestamp", result["timestamp"])

                # Display the full description, root cause, and resolution using different colored boxes
                st.markdown("**📝 Description**")
                st.write(result["description"])

                st.markdown("**🔍 Root Cause**")
                st.info(result["root_cause"]) # Blue box

                st.markdown("**✅ Resolution**")
                st.success(result["resolution"]) # Green box

# --- Data Explorer ---
st.divider()
# Add another drop-down box at the bottom to view the raw data table
with st.expander("📋 View All Incidents", expanded=False):
    # Convert the list of incidents into a Pandas DataFrame (a spreadsheet format)
    df = pd.DataFrame(incidents)
    # Remove the messy "tokens" column if it exists
    df = df.drop(columns=["tokens"], errors="ignore")
    # Display the spreadsheet on the webpage!
    st.dataframe(df, use_container_width=True)

# --- Footer ---
st.divider()
# Show some small, faded text at the very bottom
st.caption("AIOps Course — Module 1: RAG Demo Lab | Powered by Streamlit")
