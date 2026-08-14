"""
Integration Test 2: ChromaDB Vector Database Ingestion and Retrieval
This test validates the core of our AIOps pipeline — can we store an incident 
in the vector database and then retrieve it using a semantically similar query?
If this test fails, the entire RAG (Retrieval-Augmented Generation) pipeline is broken.
"""

# 'chromadb' is the vector database we use to store and search incident embeddings.
# It converts text into vectors automatically and finds the closest matches.
import chromadb


def test_chromadb_ingest_and_query():
    """Ingesting a document and querying for it should return the same document."""

    # Create an in-memory ChromaDB client.
    # 'EphemeralClient' means data lives only in RAM — perfect for testing
    # because it starts fresh every time (no leftover data from previous runs).
    client = chromadb.EphemeralClient()

    # Create a 'collection' — this is like a table in a traditional database,
    # but instead of rows and columns, it stores vectors.
    # 'hnsw:space: cosine' tells ChromaDB to use cosine similarity for matching.
    collection = client.get_or_create_collection(
        name="test_incidents",
        metadata={"hnsw:space": "cosine"},
    )

    # Ingest a known incident into the vector database.
    # ChromaDB automatically converts the 'documents' text into a 384-dim vector
    # using its built-in embedding model (all-MiniLM-L6-v2).
    collection.add(
        documents=["High CPU usage on web-server-01 caused by runaway Python process"],
        ids=["incident-001"],
        metadatas=[{"severity": "critical", "service": "web-server-01"}],
    )

    # Now query using DIFFERENT words that mean the same thing.
    # "CPU spike on server" shares no exact words with the stored incident,
    # but the vector embedding captures the semantic meaning.
    results = collection.query(query_texts=["CPU spike on server"], n_results=1)

    # Verify that ChromaDB returned exactly 1 result.
    assert len(results["documents"][0]) == 1, "Expected 1 result"

    # Verify the returned document contains "CPU" — confirming it matched
    # the correct incident, not some random unrelated one.
    assert "CPU" in results["documents"][0][0], "Expected the CPU incident to be returned"

    # Verify the ID matches — this is the strongest proof that the right
    # document was retrieved from the database.
    assert results["ids"][0][0] == "incident-001", "Expected incident-001"
