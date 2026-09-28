import uuid
from datetime import datetime
from typing import Dict


def build_chunk_metadata(source: str, page: int, chunk_text: str, section: str = "Unknown") -> Dict:
    """
    Builds the metadata dictionary attached to every chunk.
    This is what the Evidence Panel and Developer Mode will read from later.
    """
    return {
        "chunk_id": str(uuid.uuid4()),
        "source": source,
        "page": page,
        "section": section,
        "chunk_length": len(chunk_text.split()),
        "document_type": "policy",
        "created_date": datetime.utcnow().isoformat()
    }