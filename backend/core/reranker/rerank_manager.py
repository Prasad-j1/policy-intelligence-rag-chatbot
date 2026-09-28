from backend.core.reranker.cross_encoder import get_cross_encoder


def rerank_results(
    question: str,
    results: list[dict],
    top_n: int = 2,
) -> list[dict]:
    """
    Re-ranks FAISS retrieved chunks using a CrossEncoder.

    Parameters
    ----------
    question : str
        User question.

    results : list[dict]
        Retrieved chunks from FAISS.

    top_n : int
        Number of chunks to return after reranking.

    Returns
    -------
    list[dict]
        Re-ranked chunks ordered by CrossEncoder score.
    """

    if not results:
        return []

    cross_encoder = get_cross_encoder()

    sentence_pairs = [
        (question, item["chunk"])
        for item in results
    ]

    scores = cross_encoder.predict(sentence_pairs)

    for item, score in zip(results, scores):
        item["rerank_score"] = float(score)
    print("\n================ RERANK SCORES ================\n")

    for item, score in zip(results, scores):
        print("----------------------------------------")
        print(f"Score : {score:.4f}")
        print(item["chunk"][:250])
        print()

    print("===============================================\n")

    results.sort(key=lambda x: x["rerank_score"],reverse=True)

    return results[:top_n]