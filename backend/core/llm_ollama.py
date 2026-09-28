import time
import requests
from backend.config import OLLAMA_MODEL_NAME, OLLAMA_BASE_URL, LLM_TEMPERATURE
from backend.core.prompt_loader import build_grounded_prompt
from backend.utils.logger import get_logger
import json

logger = get_logger(__name__)

def _clean_answer(text: str) -> str:
    """
    Safety net against prompt-leakage: some local models continue
    generating past the intended answer and echo template markers.
    Truncates the answer at the first sign of that happening.
    """
    for marker in ["## USER QUESTION", "## RETRIEVED CONTEXT", "## YOUR ANSWER"]:
        if marker in text:
            text = text.split(marker)[0]
    return text.strip()


def generate_ollama_answer(workspace_prompt_file: str, context_chunks: list[str], question: str) -> dict:
    """
    Sends a grounded prompt to the local Ollama (Phi) model and returns
    the plain-text answer along with basic timing info.

    Used by both workspaces during development, and by PDF Chat in
    production (per the locked LLM strategy).
    """
    prompt = build_grounded_prompt(workspace_prompt_file, context_chunks, question)

    payload = {
    "model": OLLAMA_MODEL_NAME,
    "prompt": prompt,
    "stream": False,
    "options": {
        "temperature": LLM_TEMPERATURE,
        "stop": ["## USER QUESTION", "## RETRIEVED CONTEXT", "\n## "]
        }
    }
    print("=" * 60)
    print("Characters :", len(prompt))
    print("Words      :", len(prompt.split()))
    print("=" * 60)
    print(prompt)

    start_time = time.time()

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=180
        )
        response.raise_for_status()
        data = response.json()
        answer_text = _clean_answer(data.get("response", ""))

    
    except requests.exceptions.ConnectionError:
        logger.error("Ollama connection failed — is the Ollama server running?")
        return {
            "answer": "The local AI model is currently unavailable. Please make sure Ollama is running and try again.",
            "success": False,
            "provider": "ollama",
            "model": OLLAMA_MODEL_NAME,
            "response_time_seconds": round(time.time() - start_time, 2)
        }

    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out.")
        return {
            "answer": "The request took too long to process. Please try again.",
            "success": False,
            "provider": "ollama",
            "model": OLLAMA_MODEL_NAME,
            "response_time_seconds": round(time.time() - start_time, 2)
        }

    except Exception as e:
        logger.error(f"Unexpected Ollama error: {e}")
        return {
            "answer": "Something went wrong while generating the answer.",
            "success": False,
            "provider": "ollama",
            "model": OLLAMA_MODEL_NAME,
            "response_time_seconds": round(time.time() - start_time, 2)
        }
    
    if not answer_text:
        logger.warning("Ollama returned an empty response.")
        return {
            "answer": "The AI model did not return any answer. Please try again.",
            "success": False,
            "provider": "ollama",
            "model": OLLAMA_MODEL_NAME,
            "response_time_seconds": round(time.time() - start_time, 2)
        }
    response_time = round(time.time() - start_time, 2)

    # in llm_ollama.py
    return {
        "answer": answer_text,
        "success": True,
        "provider": "ollama",
        "model": OLLAMA_MODEL_NAME,
        "response_time_seconds": response_time
    }


# streaming version of the above function, used in PDF Chat for real-time token streaming
def generate_ollama_stream(
    workspace_prompt_file: str,
    context_chunks: list[str],
    question: str,
):
    """
    Streaming version of generate_ollama_answer().

    Yields tokens as Ollama generates them.

    Final response metadata (provider/model/time) is returned
    automatically when the generator finishes.
    """

    prompt = build_grounded_prompt(
        workspace_prompt_file,
        context_chunks,
        question
    )

    payload = {
        "model": OLLAMA_MODEL_NAME,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": LLM_TEMPERATURE,
            "stop": [
                "## USER QUESTION",
                "## RETRIEVED CONTEXT",
                "\n## "
            ]
        }
    }

    start_time = time.time()

    try:

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            stream=True,
            timeout=180
        )

        response.raise_for_status()

        for line in response.iter_lines():

            if not line:
                continue

            chunk = json.loads(line.decode("utf-8"))

            token = chunk.get("response", "")

            if token:
                yield {
                    "type": "token",
                    "content": token
                }

            if chunk.get("done", False):

                yield {
                    "type": "done",
                    "provider": "ollama",
                    "model": OLLAMA_MODEL_NAME,
                    "response_time_seconds": round(
                        time.time() - start_time,
                        2
                    )
                }

                break

    except requests.exceptions.ConnectionError:

        yield {
            "type": "error",
            "message": "Unable to connect to Ollama."
        }

    except requests.exceptions.Timeout:

        yield {
            "type": "error",
            "message": "Ollama request timed out."
        }

    except Exception as e:

        logger.exception(e)

        yield {
            "type": "error",
            "message": "Unexpected streaming error."
        }