# 01 — Deep Dive into Embeddings and Vector Search

In Module 1, we previewed ChromaDB. But how does it actually know which incidents are "similar" if they don't share the exact same words?

## The Problem with Keyword Search

If your current alert says: `"Database connection pool exhausted"`
But your historical incident says: `"Too many DB clients connected, reaching max_connections"`

A standard keyword search (like `grep` or Elasticsearch without NLP) will fail to match these because the words are different, even though the **meaning** is exactly the same.

## The Solution: Embeddings

Embeddings solve this by converting text into an array of numbers (a vector) that represents the *semantic meaning* of the text.

1. You pass the text to a model (like `all-MiniLM-L6-v2` via `sentence-transformers`).
2. The model outputs a high-dimensional vector (e.g., an array of 384 numbers).
3. Texts with similar meanings end up close to each other in this 384-dimensional space.

### Cosine Similarity

To find the closest match, the database calculates the **distance** (or angle) between the vectors. The smaller the distance (or the closer the cosine similarity is to 1), the more closely related the texts are.

## Vector Databases (ChromaDB)

A vector database like **ChromaDB** is optimized to store millions of these vectors and perform "Nearest Neighbor Search" extremely fast.

When a new incident occurs:
1. The new incident text is converted into a vector.
2. ChromaDB plots this new point.
3. It instantly retrieves the 3 closest historical points (your Top K results).

---

## Lab: Setting up the Data

Before we can do Vector Search, we need data. We have provided a script that generates mock IT incidents.

### Step 1: Generate the Data
Navigate to the `lab/` directory in your terminal and run the generation script:

```bash
cd lab
python generate_incidents.py
```

*You should see a message saying "Successfully generated incidents.csv".*

### Step 2: Review the Data
Open `incidents.csv`. You will see columns for `id`, `timestamp`, `service`, `severity`, `description`, `root_cause`, and `resolution`. 

Our Vector Database will embed the `description`, and when it finds a match, it will return the `root_cause` and `resolution`.

In the next lesson, we will write the code to ingest this data and feed it to an LLM!
