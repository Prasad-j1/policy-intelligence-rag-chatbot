"""
Fixed Chunker

Splits text into chunks using a fixed number of words with overlap.

This is our baseline chunking strategy and will be used for
comparison against Recursive, Semantic, and Hybrid chunkers.
"""


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """
    Split text into fixed-size overlapping chunks.

    Args:
        text:
            Input text.

        chunk_size:
            Maximum number of words per chunk.

        overlap:
            Number of words shared between consecutive chunks.

    Returns:
        List of text chunks.
    """

    if not text:
        return []

    words = text.split()

    if len(words) <= chunk_size:
        return [" ".join(words)]

    chunks = []

    step = chunk_size - overlap

    for start in range(0, len(words), step):

        end = start + chunk_size

        chunk = words[start:end]

        if not chunk:
            break

        chunks.append(" ".join(chunk))

        if end >= len(words):
            break

    return chunks