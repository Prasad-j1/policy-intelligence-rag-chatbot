from sentence_transformers import CrossEncoder

from backend.config import CROSS_ENCODER_MODEL_NAME


_cross_encoder = None


def get_cross_encoder() -> CrossEncoder:
    """
    Returns a singleton CrossEncoder model.

    The model is loaded only once during the application's lifetime.

    CrossEncoder is used after FAISS retrieval to score
    (question, chunk) pairs much more accurately than
    embedding similarity alone.
    """

    global _cross_encoder

    if _cross_encoder is None:

        print("=" * 80)
        print("Loading Cross Encoder...")
        print("=" * 80)

        _cross_encoder = CrossEncoder(
            CROSS_ENCODER_MODEL_NAME
        )

        print("=" * 80)
        print("Cross Encoder Loaded Successfully")
        print("=" * 80)

    return _cross_encoder