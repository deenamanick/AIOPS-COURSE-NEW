"""
Unit Test 1: Text Chunking Logic
This test validates that our text chunking function correctly splits large documents
into smaller overlapping pieces. Chunking is essential in AIOps because LLMs have 
token limits — you can't send an entire 10,000-line log file in one API call.
"""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split a large text string into smaller overlapping chunks.
    
    Why overlap? If we split without overlap, important context at the boundary 
    between two chunks gets lost. A 50-character overlap ensures the LLM sees 
    the full context around every split point.
    """
    chunks = []
    start = 0

    # Walk through the text, grabbing 'chunk_size' characters at a time.
    # After each chunk, we step forward by (chunk_size - overlap) so the next chunk
    # starts 50 characters before where the last one ended.
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks


def test_chunking_produces_correct_number_of_chunks():
    """A 1200-character string with chunk_size=500 and overlap=50 should produce 3 chunks."""

    # Create a simple 1200-character test string (all 'A's).
    # With chunk_size=500 and overlap=50, the step size is 450.
    # Chunk 1: chars 0-499, Chunk 2: chars 450-949, Chunk 3: chars 900-1199
    text = "A" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)

    # We expect exactly 3 chunks. If the math is wrong, the assertion fails
    # and pytest will print a clear error message showing what we got vs expected.
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"


def test_chunking_preserves_all_content():
    """Every character in the original text must appear in at least one chunk."""

    # Use a realistic sentence repeated 30 times to simulate a real log file.
    text = "The quick brown fox jumps over the lazy dog. " * 30
    chunks = chunk_text(text, chunk_size=200, overlap=20)

    # Reconstruct the full text from the chunks.
    # The first chunk is taken in full. For all subsequent chunks, we skip 
    # the first 20 characters (the overlap) to avoid double-counting.
    reconstructed = ""
    for i, chunk in enumerate(chunks):
        if i == 0:
            reconstructed += chunk
        else:
            # Skip the overlap portion — those characters already exist
            # in the previous chunk.
            reconstructed += chunk[20:]

    # The reconstructed text must be at least as long as the original.
    # If characters were lost during chunking, this assertion catches it.
    assert len(reconstructed) >= len(text), "Chunking lost content"
