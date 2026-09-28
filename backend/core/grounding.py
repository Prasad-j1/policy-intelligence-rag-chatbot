from typing import Callable
from backend.utils.logger import get_logger
import time

logger = get_logger(__name__)

NO_EVIDENCE_MESSAGE = (
    "I couldn't find sufficient supporting information in the knowledge base "
    "to answer this confidently."
)


def generate_grounded_response(
    question: str,
    retriever_fn: Callable[[str], dict],
    llm_fn: Callable[[str, list[str], str], dict],
    workspace_prompt_file: str
) -> dict:
    """
    Runs the full RAG flow, independent of any specific workspace or LLM.

    Args:
        question: the user's question
        retriever_fn: a function that takes a question and returns
                       {"chunks": [...], "results": [...], "retriever_time_seconds": float}
                       (e.g. retrieve_policy_chunks or a PDF-chat equivalent)
        llm_fn: a function that takes (workspace_prompt_file, chunks, question)
                and returns {"answer", "success", "provider", "model", "response_time_seconds"}
                (e.g. generate_gemini_answer or generate_ollama_answer)
        workspace_prompt_file: which prompt file to use (e.g. "policy_prompt.txt")

    Returns:
        A single unified response dict combining retrieval + generation results.
    """
    retrieval = retriever_fn(question)
    chunks = retrieval["chunks"]

    # No usable evidence — skip the LLM call entirely (saves tokens, avoids
    # any risk of the model answering from outside knowledge).
    if not chunks:
        logger.info("No chunks survived the similarity threshold — skipping LLM call.")
        return {
            "answer": NO_EVIDENCE_MESSAGE,
            "success": True,
            "grounded": False,
            "provider": None,
            "model": None,
            "evidence": [],
            "retriever_time_seconds": retrieval["retriever_time_seconds"],
            "response_time_seconds": retrieval["retriever_time_seconds"]
        }

    generation = llm_fn(workspace_prompt_file, chunks, question)

    return {
        "answer": generation["answer"],
        "success": generation["success"],
        "grounded": True,
        "provider": generation.get("provider"),
        "model": generation.get("model"),
        "evidence": retrieval["results"],
        "retriever_time_seconds": retrieval["retriever_time_seconds"],
        "response_time_seconds": round(
            retrieval["retriever_time_seconds"] + generation["response_time_seconds"], 2
        )
    }


import time


def generate_grounded_stream(
    question: str,
    retriever_fn,
    llm_stream_fn,
    workspace_prompt_file: str,
):
    """
    Streaming version of the RAG pipeline.

    Yields:
      token events
      final done event (contains ALL metadata)
    """

    retrieval = retriever_fn(question)

    chunks = retrieval["chunks"]

    if not chunks:

        yield {
            "type": "done",
            "answer": NO_EVIDENCE_MESSAGE,
            "grounded": False,
            "provider": None,
            "model": None,
            "evidence": [],
            "retriever_time_seconds": retrieval["retriever_time_seconds"],
            "response_time_seconds": retrieval["retriever_time_seconds"],
        }

        return

    full_answer = ""

    provider = None
    model = None
    llm_time = 0

    for event in llm_stream_fn(
        workspace_prompt_file,
        chunks,
        question,
    ):

        if event["type"] == "token":

            full_answer += event["content"]

            yield event

        elif event["type"] == "error":

            yield event
            return

        elif event["type"] == "done":

            provider = event["provider"]
            model = event["model"]
            llm_time = event["response_time_seconds"]

    yield {

        "type": "done",

        "answer": full_answer,

        "grounded": True,

        "provider": provider,

        "model": model,

        "evidence": retrieval["results"],

        "retriever_time_seconds":
            retrieval["retriever_time_seconds"],

        "response_time_seconds":
            round(
                retrieval["retriever_time_seconds"] + llm_time,
                2
            )
    }