"""
RAG Engine — Jaccard Similarity Search
Loads incident data from CSV, tokenizes descriptions, and finds the most
similar past incidents using Jaccard similarity (intersection/union of tokens).

(This docstring explains that this script searches for past incidents that share the 
most matching words with a new problem description.)
"""
# 'csv' is a built-in tool to read and write spreadsheet-like files (.csv)
import csv
# 're' stands for Regular Expressions, used for searching and replacing text patterns
import re
# 'typing' helps specify what kind of data a function expects (e.g., a List or a Dictionary)
from typing import List, Dict


# This function reads incident reports from a CSV file
def load_incidents(csv_path: str = "incidents.csv") -> List[Dict]:
    # Creates an empty list to store the incidents
    incidents = []
    # Opens the file in "read" mode ("r") as a variable 'f'
    with open(csv_path, "r") as f:
        # Reads the file line by line, treating the first row as column headers (like a dictionary)
        reader = csv.DictReader(f)
        for row in reader:
            # Breaks the 'description' into individual words ("tokens") and adds them to the row data
            row["tokens"] = tokenize(row["description"])
            # Adds the processed row into our list of incidents
            incidents.append(row)
    # Returns the final list containing all incidents
    return incidents


# This function takes a sentence and chops it into useful lowercase words (tokens)
def tokenize(text: str) -> set:
    # Converts all text to lowercase so "Server" and "server" are treated the same
    text = text.lower()
    # Uses Regular Expression (re) to remove everything except letters, numbers, and spaces (removes punctuation)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    # Splits the sentence into a list of individual words based on spaces
    words = text.split()
    
    # A list of common English words that don't add much meaning to a search (called "stop words")
    stop_words = {"the", "a", "an", "is", "was", "were", "are", "on", "in",
                  "to", "for", "of", "and", "with", "all", "from", "by", "at",
                  "due", "causing", "during", "after", "across"}
                  
    # Creates a 'set' (a collection of unique items) containing only the important words
    # It filters out the 'stop_words' and any word that is only 1 letter long
    return set(w for w in words if w not in stop_words and len(w) > 1)


# This function compares two groups of words and calculates how similar they are
def jaccard_similarity(set_a: set, set_b: set) -> float:
    # If either group is empty, they aren't similar at all (returns 0.0)
    if not set_a or not set_b:
        return 0.0
    
    # The 'intersection' (&) finds the words that appear in BOTH groups
    intersection = set_a & set_b
    # The 'union' (|) combines all unique words from BOTH groups together
    union = set_a | set_b
    
    # The similarity score is the number of shared words divided by the total number of unique words
    return len(intersection) / len(union)


# This function searches our past incidents for the ones most similar to a new query
def search(query: str, incidents: List[Dict], top_k: int = 3) -> List[Dict]:
    # First, chop the user's search query into important words (tokens)
    query_tokens = tokenize(query)
    # Create an empty list to store the results
    results = []

    # Look at every single past incident
    for incident in incidents:
        # Calculate how similar the query words are to the incident's words
        score = jaccard_similarity(query_tokens, incident["tokens"])
        
        # If they share at least some words (score > 0), add it to our results
        if score > 0:
            results.append({
                "id": incident["id"],
                "timestamp": incident["timestamp"],
                "severity": incident["severity"],
                "service": incident["service"],
                "description": incident["description"],
                "root_cause": incident["root_cause"],
                "resolution": incident["resolution"],
                "similarity_score": round(score, 4), # Round the score to 4 decimal places
            })

    # Sort the results so the ones with the HIGHEST score are at the top (reverse=True)
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    # Return only the top 'top_k' number of results (default is 3)
    return results[:top_k]


# This runs only if the file is executed directly (not imported by another script)
if __name__ == "__main__":
    # Load all the data from the CSV file
    data = load_incidents()
    print(f"Loaded {len(data)} incidents.\n")

    # A list of test searches to see if our search engine works
    test_queries = [
        "database connection pool exhausted",
        "high CPU usage on server",
        "disk space running low",
        "nginx 502 bad gateway error",
    ]

    # Go through each test search one by one
    for q in test_queries:
        print(f"Query: \"{q}\"")
        # Run the search function!
        hits = search(q, data)
        # Print out the results found
        for hit in hits:
            print(f"  [{hit['severity']}] Score: {hit['similarity_score']} — {hit['description'][:80]}...")
        print()
