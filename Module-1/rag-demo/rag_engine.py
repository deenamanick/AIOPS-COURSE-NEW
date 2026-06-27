"""
RAG Engine — Jaccard Similarity Search
Loads incident data from CSV, tokenizes descriptions, and finds the most
similar past incidents using Jaccard similarity (intersection/union of tokens).
"""
import csv
import re
from typing import List, Dict


def load_incidents(csv_path: str = "incidents.csv") -> List[Dict]:
    """Load incident records from CSV file."""
    incidents = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["tokens"] = tokenize(row["description"])
            incidents.append(row)
    return incidents


def tokenize(text: str) -> set:
    """Convert text to a set of lowercase tokens, removing punctuation."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    words = text.split()
    # Remove common stop words that add noise
    stop_words = {"the", "a", "an", "is", "was", "were", "are", "on", "in",
                  "to", "for", "of", "and", "with", "all", "from", "by", "at",
                  "due", "causing", "during", "after", "across"}
    return set(w for w in words if w not in stop_words and len(w) > 1)


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Calculate Jaccard similarity: |A ∩ B| / |A ∪ B|"""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def search(query: str, incidents: List[Dict], top_k: int = 3) -> List[Dict]:
    """Find top-k incidents most similar to the query using Jaccard similarity."""
    query_tokens = tokenize(query)
    results = []

    for incident in incidents:
        score = jaccard_similarity(query_tokens, incident["tokens"])
        if score > 0:
            results.append({
                "id": incident["id"],
                "timestamp": incident["timestamp"],
                "severity": incident["severity"],
                "service": incident["service"],
                "description": incident["description"],
                "root_cause": incident["root_cause"],
                "resolution": incident["resolution"],
                "similarity_score": round(score, 4),
            })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    # Quick CLI test
    data = load_incidents()
    print(f"Loaded {len(data)} incidents.\n")

    test_queries = [
        "database connection pool exhausted",
        "high CPU usage on server",
        "disk space running low",
        "nginx 502 bad gateway error",
    ]

    for q in test_queries:
        print(f"Query: \"{q}\"")
        hits = search(q, data)
        for hit in hits:
            print(f"  [{hit['severity']}] Score: {hit['similarity_score']} — {hit['description'][:80]}...")
        print()
