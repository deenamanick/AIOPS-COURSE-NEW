"""Unit Test 1: Validate text chunking logic."""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def test_chunking_produces_correct_number_of_chunks():
    """A 1200-character string with chunk_size=500 and overlap=50 should produce 3 chunks."""
    text = "A" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"


def test_chunking_preserves_all_content():
    """Every character in the original text must appear in at least one chunk."""
    text = "The quick brown fox jumps over the lazy dog. " * 30
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    reconstructed = ""
    for i, chunk in enumerate(chunks):
        if i == 0:
            reconstructed += chunk
        else:
            reconstructed += chunk[20:]
    assert len(reconstructed) >= len(text), "Chunking lost content"
