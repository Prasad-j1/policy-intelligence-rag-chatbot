from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class SemanticChunker:
    """
    Semantic chunker.

    Instead of splitting by character count,
    this chunker splits whenever the meaning
    between neighbouring paragraphs changes.

    Pipeline

        Document
            ↓
        Paragraphs
            ↓
        Sentence Embeddings
            ↓
        Similarity Comparison
            ↓
        Semantic Chunks
    """

    def __init__(self, similarity_threshold: float = 0.75):

        self.similarity_threshold = similarity_threshold

        self.embedding_model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )
    def _split_into_paragraphs(self, text: str) -> list[str]:
        """
        Split a document into paragraphs.

        Empty paragraphs are removed.
        """

        paragraphs = [
            paragraph.strip()
            for paragraph in text.split("\n\n")
            if paragraph.strip()
        ]

        return paragraphs


    def _embed_paragraphs(
        self,
        paragraphs: list[str]
    ) -> np.ndarray:
        """
        Convert every paragraph into an embedding vector.
        """

        if not paragraphs:
            return np.array([])

        embeddings = self.embedding_model.encode(
            paragraphs,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        return embeddings
    def _compute_similarities(
        self,
        embeddings: np.ndarray
    ) -> list[float]:
        """
        Compute cosine similarity between neighbouring paragraphs.
        """

        if len(embeddings) < 2:
            return []

        similarities = []

        for i in range(len(embeddings) - 1):

            similarity = cosine_similarity(
                embeddings[i].reshape(1, -1),
                embeddings[i + 1].reshape(1, -1)
            )[0][0]

            similarities.append(float(similarity))

        return similarities
    def _build_chunks(
        self,
        paragraphs: list[str],
        similarities: list[float]
    ) -> list[str]:
        """
        Merge neighbouring paragraphs until the similarity
        falls below the configured threshold.
        """

        if not paragraphs:
            return []

        chunks = []

        current_chunk = [paragraphs[0]]

        for i, similarity in enumerate(similarities):

            if similarity >= self.similarity_threshold:

                current_chunk.append(
                    paragraphs[i + 1]
                )

            else:

                chunks.append(
                    "\n\n".join(current_chunk)
                )

                current_chunk = [
                    paragraphs[i + 1]
                ]

        if current_chunk:

            chunks.append(
                "\n\n".join(current_chunk)
            )

        return chunks
    def split(self, text: str) -> list[str]:
        """
        Public method used by the retriever.

        Pipeline:

            Text
                ↓
            Paragraphs
                ↓
            Embeddings
                ↓
            Similarity Scores
                ↓
            Semantic Chunks
        """

        if not text.strip():
            return []

        paragraphs = self._split_into_paragraphs(text)

        if len(paragraphs) <= 1:
            return paragraphs

        embeddings = self._embed_paragraphs(paragraphs)

        similarities = self._compute_similarities(
            embeddings
        )

        chunks = self._build_chunks(
            paragraphs,
            similarities
        )

        return chunks

_semantic_chunker = SemanticChunker()


def chunk_text(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None
) -> list[str]:
    """
    Compatibility wrapper.

    Keeps the same API as FixedChunker and RecursiveChunker
    so chunk_manager.py never needs to know which chunker
    is being used.
    """

    return _semantic_chunker.split(text)