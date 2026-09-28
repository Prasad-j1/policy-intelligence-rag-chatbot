from backend.core.chunkers.fixed_chunker import chunk_text as fixed_chunk
from backend.core.chunkers.recursive_chunker import chunk_text as recursive_chunk
from backend.core.chunkers.semantic_chunker import chunk_text as semantic_chunk

# Map each document type to its preferred chunker.
CHUNKER_MAP = {
    "resume": recursive_chunk,
    "policy": semantic_chunk,
    "handbook": semantic_chunk,
    "markdown": recursive_chunk,
    "default": fixed_chunk,
}


def chunk_document(
    text: str,
    document_type: str = "default",
) -> list[str]:
    """
    Returns chunks using the most appropriate chunking strategy
    for the given document type.
    """

    document_type = document_type.lower()

    chunker = CHUNKER_MAP.get(
        document_type,
        CHUNKER_MAP["default"]
    )

    return chunker(text)