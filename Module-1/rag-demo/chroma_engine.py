"""
Bonus: ChromaDB Vector Search Engine
Upgrades from Jaccard (keyword matching) to semantic vector search.
Uses sentence-transformers to embed incident descriptions and ChromaDB for storage/query.
This is a preview for Module 2.

(This script uses advanced AI techniques to search by 'meaning' rather than exact word matches.)
"""
import csv
from typing import List, Dict

# 'try' tells Python to attempt running this code. If it fails (like if a tool isn't installed),
# it will jump to the 'except' block instead of crashing the whole program.
try:
    import chromadb
    CHROMA_AVAILABLE = True # If import succeeds, set this flag to True
except ImportError:
    CHROMA_AVAILABLE = False # If import fails, set this flag to False


# This function loads CSV data and saves it into a special AI database called ChromaDB
def load_and_embed(csv_path: str = "incidents.csv", chroma_host: str = "chromadb", chroma_port: int = 8000):
    # If the chromadb library wasn't found, stop and show an error message
    if not CHROMA_AVAILABLE:
        raise RuntimeError("chromadb not installed. Run: pip install chromadb")

    # Connect to the ChromaDB server running over the network
    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

    # Try to delete the existing "incidents" database collection if it exists, so we can start fresh
    try:
        client.delete_collection("incidents")
    except Exception:
        pass # If it doesn't exist yet, just ignore the error (pass)

    # Create a new database collection to hold our incident data
    # "cosine" is a mathematical way to measure how close two AI vectors (meanings) are to each other
    collection = client.create_collection(
        name="incidents",
        metadata={"hnsw:space": "cosine"}
    )

    # Read the incidents from the CSV file into a list, just like in rag_engine.py
    incidents = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            incidents.append(row)

    # Add all the documents to ChromaDB.
    # ChromaDB will automatically convert the text ("documents") into AI numbers ("embeddings")
    # 'metadatas' allows us to store extra info (like severity, service) alongside the text
    collection.add(
        documents=[inc["description"] for inc in incidents],
        metadatas=[{
            "severity": inc["severity"],
            "service": inc["service"],
            "root_cause": inc["root_cause"],
            "resolution": inc["resolution"],
            "timestamp": inc["timestamp"],
        } for inc in incidents],
        ids=[inc["id"] for inc in incidents], # Every document needs a unique ID
    )

    print(f"Embedded {len(incidents)} incidents into ChromaDB.")
    return collection # Return the ready-to-use database collection


# This function searches the AI database for similar incidents
def search_chroma(query: str, collection, top_k: int = 3) -> List[Dict]:
    # Query the collection with our search text
    # 'n_results=top_k' tells it how many top matches we want back
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )

    # Create an empty list to organize the messy raw data returned by ChromaDB
    hits = []
    
    # Loop through the results (ChromaDB returns lists inside of lists, hence the [0][i])
    for i in range(len(results["ids"][0])):
        # Package the result into a clean dictionary and add it to our 'hits' list
        hits.append({
            "id": results["ids"][0][i],
            "description": results["documents"][0][i],
            "severity": results["metadatas"][0][i]["severity"],
            "service": results["metadatas"][0][i]["service"],
            "root_cause": results["metadatas"][0][i]["root_cause"],
            "resolution": results["metadatas"][0][i]["resolution"],
            "timestamp": results["metadatas"][0][i]["timestamp"],
            "distance": round(results["distances"][0][i], 4), # Distance measures how "far apart" the meanings are
        })

    return hits


# This block runs only if you execute this file directly
if __name__ == "__main__":
    print("Loading incidents into ChromaDB...")
    # Setup the database by running the load function
    col = load_and_embed()

    # Some test phrases to search for
    test_queries = [
        "database connection pool exhausted",
        "server running out of memory slowly",
        "certificate expired HTTPS not working",
    ]

    # Run a search for each test phrase and print the results
    for q in test_queries:
        print(f"\nQuery: \"{q}\"")
        hits = search_chroma(q, col)
        for hit in hits:
            # Lower distance means the AI thinks the meanings are closer together!
            print(f"  [{hit['severity']}] Distance: {hit['distance']} — {hit['description'][:80]}...")
