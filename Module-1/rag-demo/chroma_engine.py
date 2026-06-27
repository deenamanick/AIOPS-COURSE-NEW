"""
Bonus: ChromaDB Vector Search Engine
Upgrades from Jaccard (keyword matching) to semantic vector search.
Uses sentence-transformers to embed incident descriptions and ChromaDB for storage/query.
This is a preview for Module 2.
"""
import csv
from typing import List, Dict

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


def load_and_embed(csv_path: str = "incidents.csv", chroma_host: str = "chromadb", chroma_port: int = 8000):
    """Load incidents from CSV and store embeddings in ChromaDB."""
    if not CHROMA_AVAILABLE:
        raise RuntimeError("chromadb not installed. Run: pip install chromadb")

    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

    # Delete existing collection if re-running
    try:
        client.delete_collection("incidents")
    except Exception:
        pass

    collection = client.create_collection(
        name="incidents",
        metadata={"hnsw:space": "cosine"}
    )

    incidents = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            incidents.append(row)

    # Add documents to ChromaDB (it uses its own default embedding function)
    collection.add(
        documents=[inc["description"] for inc in incidents],
        metadatas=[{
            "severity": inc["severity"],
            "service": inc["service"],
            "root_cause": inc["root_cause"],
            "resolution": inc["resolution"],
            "timestamp": inc["timestamp"],
        } for inc in incidents],
        ids=[inc["id"] for inc in incidents],
    )

    print(f"Embedded {len(incidents)} incidents into ChromaDB.")
    return collection


def search_chroma(query: str, collection, top_k: int = 3) -> List[Dict]:
    """Search for similar incidents using ChromaDB vector similarity."""
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )

    hits = []
    for i in range(len(results["ids"][0])):
        hits.append({
            "id": results["ids"][0][i],
            "description": results["documents"][0][i],
            "severity": results["metadatas"][0][i]["severity"],
            "service": results["metadatas"][0][i]["service"],
            "root_cause": results["metadatas"][0][i]["root_cause"],
            "resolution": results["metadatas"][0][i]["resolution"],
            "timestamp": results["metadatas"][0][i]["timestamp"],
            "distance": round(results["distances"][0][i], 4),
        })

    return hits


if __name__ == "__main__":
    print("Loading incidents into ChromaDB...")
    col = load_and_embed()

    test_queries = [
        "database connection pool exhausted",
        "server running out of memory slowly",
        "certificate expired HTTPS not working",
    ]

    for q in test_queries:
        print(f"\nQuery: \"{q}\"")
        hits = search_chroma(q, col)
        for hit in hits:
            print(f"  [{hit['severity']}] Distance: {hit['distance']} — {hit['description'][:80]}...")
