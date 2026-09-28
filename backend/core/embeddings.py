from langchain_community.embeddings import HuggingFaceEmbeddings
from backend.config import EMBEDDING_MODEL_NAME

# Module-level cache so the model is loaded into memory only once,
# no matter how many times get_embedding_model() is called.
_embedding_model = None


def get_embedding_model():
    """
    Returns a shared instance of the BGE embedding model.
    Used by:
      - build_index.py (embeds all knowledge base chunks)
      - retriever.py (embeds the user's question at query time)
    Loading it once and reusing it avoids reloading the model on
    every request, which would be slow.
    """
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )

    return _embedding_model