from functools import partial
from backend.config import POLICY_ASSISTANT_LLM, PDF_CHAT_LLM
from backend.core.retriever import retrieve_policy_chunks
from backend.core.retriever_pdf import retrieve_pdf_chunks  # built next
from backend.core.llm_gemini import generate_gemini_answer
from backend.core.llm_ollama import generate_ollama_answer
from backend.core.grounding import generate_grounded_response
from backend.utils.logger import get_logger
from backend.core.llm_gemini import generate_gemini_stream
from backend.core.guardrails import check_query_guardrail
from backend.core.llm_ollama import (
    generate_ollama_answer,
    generate_ollama_stream
)

from backend.core.grounding import (
    generate_grounded_response,
    generate_grounded_stream,
)
from backend.core.llm_ollama import generate_ollama_stream

from backend.core.llm_gemini import (
    generate_gemini_answer,
    generate_gemini_stream,
)

from backend.core.llm_nvidia import (
    generate_nvidia_answer,
    generate_nvidia_stream,
)

# LLM_FUNCTIONS = {
#     "gemini": generate_gemini_answer,
#     "ollama": generate_ollama_answer,
# }
LLM_FUNCTIONS = {
    "gemini": generate_gemini_answer,
    "ollama": generate_ollama_answer,
    "nvidia": generate_nvidia_answer,
}


# LLM_STREAM_FUNCTIONS = {
#     "ollama": generate_ollama_stream,
#     "gemini": generate_gemini_stream,
# }

LLM_STREAM_FUNCTIONS = {
    "ollama": generate_ollama_stream,
    "gemini": generate_gemini_stream,
    "nvidia": generate_nvidia_stream,
}


logger = get_logger(__name__)

# ------------------------------------------------------------
# WORKSPACE CONFIGURATION
# The ONLY place in the entire app that maps a workspace name to
# its LLM provider, prompt file, and retriever. Nothing else in
# the codebase should hardcode these associations.
# ------------------------------------------------------------

WORKSPACE_CONFIG = {
    "policy": {
        "llm_provider": POLICY_ASSISTANT_LLM,       # from .env
        "prompt_file": "policy_prompt.txt",
    },
    "pdf_chat": {
        "llm_provider": PDF_CHAT_LLM,                # from .env
        "prompt_file": "pdf_chat_prompt.txt",
    },
}

# LLM_FUNCTIONS = {
#     "gemini": generate_gemini_answer,
#     "ollama": generate_ollama_answer,
#     "nvidia": generate_nvidia_answer,
# }


def _get_llm_function(workspace: str, provider: str | None = None):
    """
    Reads which LLM provider a workspace is configured to use
    and returns the matching non-streaming function.
    """

    provider = provider or WORKSPACE_CONFIG[workspace]["llm_provider"]

    llm_fn = LLM_FUNCTIONS.get(provider)

    if llm_fn is None:
        raise ValueError(
            f"Unknown LLM provider '{provider}' for workspace '{workspace}'."
        )

    return llm_fn

def _get_llm_stream_function(workspace: str, provider: str | None = None):

    provider = provider or WORKSPACE_CONFIG[workspace]["llm_provider"]

    llm_stream_fn = LLM_STREAM_FUNCTIONS.get(provider)

    if llm_stream_fn is None:
        raise ValueError(
            f"Streaming not supported for provider '{provider}'."
        )

    return llm_stream_fn

def _get_stream_llm_function(workspace: str):
    """
    Returns the streaming LLM function for the workspace.

    At the moment only Ollama supports streaming.
    """

    provider = WORKSPACE_CONFIG[workspace]["llm_provider"]

    llm_fn = LLM_STREAM_FUNCTIONS.get(provider)

    if llm_fn is None:
        raise ValueError(
            f"Streaming is not supported for provider '{provider}'."
        )

    return llm_fn


def _get_retriever_function(workspace: str, session_id: str | None = None):
    """
    Returns the correct retriever function for the workspace.
    Policy Assistant always searches the permanent knowledge base.
    PDF Chat searches a temporary, session-specific index, so we
    bind (partial) the session_id into the function here.
    """
    if workspace == "policy":
        return retrieve_policy_chunks

    if workspace == "pdf_chat":
        if not session_id:
            raise ValueError("session_id is required for the pdf_chat workspace.")
        return partial(retrieve_pdf_chunks, session_id=session_id)

    raise ValueError(f"Unknown workspace '{workspace}'.")


def route_query(workspace: str,question: str,session_id: str | None = None,provider: str | None = None,):
    """
    Main entry point called by the API layer.

    Selects the correct retriever, LLM, and prompt file for the given
    workspace, then runs the full grounded RAG flow via grounding.py.

    Args:
        workspace: "policy" or "pdf_chat"
        question: the user's question
        session_id: required only for pdf_chat (identifies which temp
                    FAISS index to search)
        provider: the LLM provider to use (optional)

    Returns:
        The unified response dict from generate_grounded_response().
    """

    guardrail = check_query_guardrail(question)
    if not guardrail.allowed:
        raise ValueError(f"Query rejected: {guardrail.reason}")

    if workspace not in WORKSPACE_CONFIG:
        raise ValueError(f"Unknown workspace '{workspace}'. Expected 'policy' or 'pdf_chat'.")

    prompt_file = WORKSPACE_CONFIG[workspace]["prompt_file"]

    # llm_fn = _get_llm_function(workspace)
    llm_fn = _get_llm_function(workspace,provider)
    retriever_fn = _get_retriever_function(workspace, session_id)
    logger.info(
        f"Routing query -> workspace='{workspace}', "
        f"provider='{provider or WORKSPACE_CONFIG[workspace]['llm_provider']}'"
    )

    return generate_grounded_response(
        question=question,
        retriever_fn=retriever_fn,
        llm_fn=llm_fn,
        workspace_prompt_file=prompt_file
    )

def route_query_stream(
    workspace: str,
    question: str,
    session_id: str | None = None,
    provider: str | None = None,            
):
    """
    Streaming version of route_query().
    """
    guardrail = check_query_guardrail(question)
    if not guardrail.allowed:
        raise ValueError(f"Query rejected: {guardrail.reason}")

    if workspace not in WORKSPACE_CONFIG:
        raise ValueError(
            f"Unknown workspace '{workspace}'."
        )

    prompt_file = WORKSPACE_CONFIG[workspace]["prompt_file"]

    llm_stream_fn = _get_llm_stream_function(workspace,provider)

    retriever_fn = _get_retriever_function(
        workspace,
        session_id
    )

    logger.info(
        f"Streaming query -> workspace='{workspace}', "
        f"provider='{WORKSPACE_CONFIG[workspace]['llm_provider']}'"
    )

    return generate_grounded_stream(
        question=question,
        retriever_fn=retriever_fn,
        llm_stream_fn=llm_stream_fn,
        workspace_prompt_file=prompt_file,
    )