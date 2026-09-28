import json
import time
import faiss
import numpy as np
from pathlib import Path
from backend.config import VECTOR_STORE_PATH, TOP_K, SIMILARITY_THRESHOLD
from backend.core.embeddings import get_embedding_model
from backend.core.similarity import l2_distance_to_similarity
from backend.utils.logger import get_logger
from backend.core.reranker.rerank_manager import rerank_results

logger = get_logger(__name__)

# Module-level cache so the FAISS index and metadata are loaded from
# disk only once, not on every single query.
_index = None
_chunks = None
_metadata = None


def _load_permanent_index():
    """
    Loads the permanent FAISS index and its matching metadata.json
    from disk. Cached after the first call.
    """
    global _index, _chunks, _metadata

    if _index is None:
        index_path = Path(VECTOR_STORE_PATH) / "permanent" / "index.faiss"
        metadata_path = Path(VECTOR_STORE_PATH) / "permanent" / "metadata.json"

        if not index_path.exists():
            raise FileNotFoundError(
                "Permanent FAISS index not found. Run build_index.py first."
            )

        _index = faiss.read_index(str(index_path))

        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _chunks = data["chunks"]
            _metadata = data["metadata"]

        logger.info(f"Loaded permanent FAISS index with {len(_chunks)} chunks.")

    return _index, _chunks, _metadata



def retrieve_policy_chunks(question: str) -> dict:
    """
    Retrieves the top-K most relevant chunks from the permanent
    Policy knowledge base for a given question.

    Returns:
        {
            "chunks": [str, ...]          # plain text, sent to the LLM
            "results": [ {chunk, metadata, similarity_score}, ... ]  # full detail, for Evidence Panel
            "retriever_time_seconds": float
        }
    """
    start_time = time.time()

    index, chunks, metadata = _load_permanent_index()

    embedding_model = get_embedding_model()
    query_vector = embedding_model.embed_query(question)
    query_vector = np.array([query_vector]).astype("float32")

    distances, indices = index.search(query_vector, TOP_K)

    results = []
    for distance, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue  # FAISS returns -1 when there aren't enough matches

        similarity_score = l2_distance_to_similarity(distance)

        if similarity_score < SIMILARITY_THRESHOLD:
            continue  # below threshold, discard

        results.append({
            "chunk": chunks[idx],
            "metadata": metadata[idx],
            "similarity_score": round(similarity_score, 4)
        })

            # -------------------------------------------------------
        # Re-rank retrieved chunks
        # -------------------------------------------------------

        results = rerank_results(
            question=question,
            results=results,
            top_n=3
        )

        retriever_time = round(time.time() - start_time, 2)

        logger.info(
            f"Retrieved {len(results)} chunks "
            f"after reranking in {retriever_time}s."
        )

        for i, item in enumerate(results, start=1):

            logger.info(
                f"Rank {i} | "
                f"CrossEncoder={item['rerank_score']:.4f} | "
                f"Embedding={item['similarity_score']:.4f}"
            )

        return {
            "chunks": [r["chunk"] for r in results],
            "results": results,
            "retriever_time_seconds": retriever_time
        }