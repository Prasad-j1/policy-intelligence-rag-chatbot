def l2_distance_to_similarity(distance: float) -> float:
    """
    Converts FAISS L2 distance into a 0-1 similarity score.

    This only works correctly because our embeddings are normalized
    (see embeddings.py — normalize_embeddings=True). For normalized
    vectors, L2 distance and cosine similarity are mathematically
    related by:

        similarity = 1 - (distance^2 / 2)

    Without normalization, this formula would not hold, and
    SIMILARITY_THRESHOLD would not mean what config.py claims it means.

    Used by both retriever.py (permanent knowledge base) and
    retriever_pdf.py (temporary uploaded PDF sessions), so the exact
    same scoring logic applies everywhere in the app.
    """
    similarity = 1 - (distance ** 2) / 2
    return max(0.0, min(1.0, similarity))  # clamp to [0, 1]