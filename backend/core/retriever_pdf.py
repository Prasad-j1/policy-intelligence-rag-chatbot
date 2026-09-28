import time
import faiss
import numpy as np
from backend.config import TOP_K, SIMILARITY_THRESHOLD
from backend.core.embeddings import get_embedding_model
from backend.core.similarity import l2_distance_to_similarity  # shared helper, see note below
from backend.ingestion.loader import load_pdf
from backend.ingestion.cleaner import clean_text
from backend.ingestion.chunker import chunk_text
from backend.ingestion.metadata import build_chunk_metadata
from backend.config import CHUNK_SIZE, CHUNK_OVERLAP
# from backend.config import PDF_CHUNK_SIZE, PDF_CHUNK_OVERLAP
from backend.utils.logger import get_logger

from backend.core.reranker.rerank_manager import rerank_results
from backend.core.chunkers.chunk_manager import chunk_document

logger = get_logger(__name__)

# In-memory store of active PDF Chat sessions.
# Structure: { session_id: {"index": faiss.Index, "chunks": [...], "metadata": [...]} }
_temp_sessions: dict = {}



def build_temp_index(session_id: str, file_path: str, original_filename: str) -> int:
    """
    Called once, right after a user uploads a PDF.
    Loads, cleans, chunks, embeds, and indexes the PDF — all in memory,
    scoped to this session_id only. Overwrites any existing session
    with the same ID (matches the "uploading a new PDF ends the old
    session" rule).
    """
    logger.info(f"Building temp index for session '{session_id}' from {file_path}")

    import time
    t0 = time.time()
    pages = load_pdf(file_path)
    print(f"Reading PDF: {time.time()-t0:.2f}s")

    chunks = []
    metadata = []

    for page in pages:

        cleaned = clean_text(page["text"])

        if not cleaned:
            continue

        # page_chunks = chunk_document(

        #     text=cleaned,

        #     document_type="resume"
        # )

        page_chunks  = chunk_document(
            text=cleaned,
            document_type="resume"
        )
        print("="*60)
        print("Semantic Chunks ",len(chunks))

        for i,chunk in enumerate(chunks):
            print("\nChunk ",i+1)
            print("="*60)
            print(chunk[:400])


        for chunk in page_chunks:

            chunk_meta = build_chunk_metadata(

                source=original_filename,

                page=page["page"],

                chunk_text=chunk,

                section="Uploaded Document"

            )

            chunks.append(chunk)

            metadata.append(chunk_meta)

    if not chunks:
        raise ValueError("No readable text found in the uploaded PDF.")
    print(f"Chunks created: {len(chunks)}")
    print(f"Chunks Created : {len(chunks)}")
    import time
    t1 = time.time()
    print("Before get_embedding_model()")
    embedding_model = get_embedding_model()
    print("After get_embedding_model()")

    print("Before embed_documents()")
    embeddings = embedding_model.embed_documents(chunks)
    print("After embed_documents()")
    print(f"Embedding Time : {time.time()-t1:.2f}s")
    print(f"Embedding Time: {time.time()-t1:.2f}s")
    embeddings = np.array(embeddings).astype("float32")

    faiss.normalize_L2(embeddings)

    t2 = time.time()

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    print(f"FAISS Time : {time.time()-t2:.2f}s")


    _temp_sessions[session_id] = {
        "index": index,
        "chunks": chunks,
        "metadata": metadata
    }

    logger.info(f"Temp index ready for session '{session_id}' — {len(chunks)} chunks.")
    return len(chunks)


def retrieve_pdf_chunks(question: str, session_id: str) -> dict:
    """
    Searches a specific session's temporary FAISS index.
    Same return shape as retrieve_policy_chunks(), so grounding.py
    can treat both retrievers identically.
    """
    start_time = time.time()

    session = _temp_sessions.get(session_id)
    if session is None:
        raise ValueError(
            f"No active PDF Chat session found for session_id '{session_id}'. "
            "Upload a PDF first."
        )

    index = session["index"]
    chunks = session["chunks"]
    metadata = session["metadata"]

    print("Before get_embedding_model()")

    embedding_model = get_embedding_model()
    
    query_vector = embedding_model.embed_query(question)
    query_vector = np.array([query_vector]).astype("float32")

    faiss.normalize_L2(query_vector)

    k = min(TOP_K, len(chunks))  # can't search for more chunks than exist

    
    distances, indices = index.search(query_vector, k)

    print("\n========== FAISS RESULTS ==========\n")

    for rank, (distance, idx) in enumerate(zip(distances[0], indices[0]), start=1):

        if idx == -1:
            continue

        similarity = l2_distance_to_similarity(distance)

        print(f"Rank {rank}")
        print(f"Index: {idx}")
        print(f"Similarity: {similarity:.4f}")
        print(chunks[idx][:400])
        print("----------------------------------")

    results = []

    for distance, idx in zip(distances[0], indices[0]):

        if idx == -1:
            continue

        similarity_score = l2_distance_to_similarity(distance)

        if similarity_score < SIMILARITY_THRESHOLD:
            continue

        results.append({
            "chunk": chunks[idx],
            "metadata": metadata[idx],
            "similarity_score": round(similarity_score, 4)
        })

    # ← Loop ends here

    print("\n========== FAISS RESULTS ==========\n")

    for i, item in enumerate(results, start=1):
        print(f"Result {i}")
        print(f"Embedding Score: {item['similarity_score']:.4f}")
        print(item["chunk"][:300])
        print("----------------------------------")

    results = rerank_results(
        question=question,
        results=results,
        top_n=3
    )

    retriever_time = round(time.time() - start_time, 2)

    logger.info(
        f"[session={session_id}] Retrieved {len(results)} chunks after reranking in {retriever_time}s."
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



def clear_temp_session(session_id: str) -> None:
    """
    Deletes a session's temporary index, chunks, and metadata from
    memory. Called when the user clicks "Clear Workspace" or uploads
    a new PDF (which internally calls this before build_temp_index()).
    """
    if session_id in _temp_sessions:
        del _temp_sessions[session_id]
        logger.info(f"Cleared temp session '{session_id}'.")
    else:
        logger.warning(f"Attempted to clear non-existent session '{session_id}'.")


