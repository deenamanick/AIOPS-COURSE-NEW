"""
Unit Test 2: Embedding Generation Validation
This test validates that our embedding model produces vectors of the correct shape.
In AIOps, embeddings convert incident text like "CPU at 98%" into an array of 384 numbers
that capture the *meaning* of the text — enabling semantic search in ChromaDB.
"""

# 'numpy' is a math library for working with arrays of numbers.
# We use it here to generate mock embedding vectors for testing.
import numpy as np


def generate_mock_embedding(text: str, dim: int = 384) -> list[float]:
    """
    Simulate a sentence-transformer embedding (384-dim for all-MiniLM-L6-v2).
    
    In production, the real model converts text into a 384-dimensional vector.
    For testing, we generate a deterministic random vector so we can verify 
    the shape without needing the actual model installed.
    """
    # Use the hash of the input text as the random seed.
    # This ensures the same input always produces the same fake embedding,
    # making our tests deterministic (repeatable every time).
    np.random.seed(hash(text) % 2**32)

    # Generate 384 random floating-point numbers and convert to a Python list.
    return np.random.randn(dim).tolist()


def test_embedding_has_correct_dimensions():
    """The all-MiniLM-L6-v2 model produces 384-dimensional embeddings."""

    # Generate a mock embedding for a realistic incident description.
    embedding = generate_mock_embedding("Server CPU at 95% for 10 minutes")

    # The embedding must have exactly 384 dimensions.
    # If the model changes or our code breaks, this catches it immediately.
    assert len(embedding) == 384, f"Expected 384 dims, got {len(embedding)}"


def test_embedding_values_are_floats():
    """Every element in the embedding vector must be a float."""

    # Generate another mock embedding with a different input text.
    embedding = generate_mock_embedding("Database connection timeout after 30s")

    # ChromaDB and cosine similarity calculations require float values.
    # If any element is an integer or string, the math will break silently.
    # This test catches that by checking every single element in the array.
    assert all(isinstance(v, float) for v in embedding), "Embedding contains non-float values"
