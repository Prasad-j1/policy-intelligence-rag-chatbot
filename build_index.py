from backend.ingestion.loader import load_knowledge_base
from backend.ingestion.cleaner import clean_text
from backend.ingestion.chunker import chunk_text
from backend.ingestion.metadata import build_chunk_metadata

from backend.core.embeddings import get_embedding_model  # built in a later step

from backend.config import (
    KNOWLEDGE_BASE_PATH,
    VECTOR_STORE_PATH,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)
import faiss
import numpy as np
import json


def build_index():
    print("Step 1: Loading PDFs...")
    documents = load_knowledge_base(KNOWLEDGE_BASE_PATH)

    all_chunks = []
    all_metadata = []

    print("Step 2: Cleaning + chunking...")
    for doc in documents:
        source = doc["source"]
        current_section = "General"  # fallback if no heading found yet

        for page in doc["pages"]:
            # Update current_section if this page introduced a new heading
            if page["headings"]:
                current_section = page["headings"][0]  # first heading on the page

            cleaned = clean_text(page["text"])
            if not cleaned:
                continue

            chunks = chunk_text(cleaned, CHUNK_SIZE, CHUNK_OVERLAP)

            for chunk in chunks:
                metadata = build_chunk_metadata(source, page["page"], chunk, section=current_section)
                all_chunks.append(chunk)
                all_metadata.append(metadata)

    print(f"Total chunks created: {len(all_chunks)}")

    print("Step 3: Generating embeddings...")
    embedding_model = get_embedding_model()
    embeddings = embedding_model.embed_documents(all_chunks)
    embeddings = np.array(embeddings).astype("float32")

    print("Step 4: Building FAISS index...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    print("Step 5: Persisting index + metadata to disk...")
    faiss.write_index(index, f"{VECTOR_STORE_PATH}/permanent/index.faiss")

    with open(f"{VECTOR_STORE_PATH}/permanent/metadata.json", "w") as f:
        json.dump({"chunks": all_chunks, "metadata": all_metadata}, f, indent=2)

    print("✅ Index build complete.")


if __name__ == "__main__":
    build_index()