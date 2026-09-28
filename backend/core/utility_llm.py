from unittest import result

import requests
from backend.config import OLLAMA_MODEL_NAME, OLLAMA_BASE_URL
from backend.core.prompt_loader import load_prompt
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def generate_utility_text(prompt_file: str, input_text: str, max_tokens: int = 30) -> str:
    """
    Lightweight LLM call for small utility tasks (title generation,
    follow-up questions) — no grounding rules, no context chunks,
    no evidence. Just an instruction + input, output text back.

    Always uses Ollama, regardless of workspace LLM config — these
    are cheap, low-stakes tasks that don't need Gemini's quality,
    and keeping them on Ollama saves API tokens.
    """
    instructions = load_prompt(prompt_file)
    full_prompt = f"{instructions}\n\nInput:\n{input_text}\n\nOutput:"

    payload = {
        "model": OLLAMA_MODEL_NAME,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": max_tokens,
            "stop": ["\n\n", "Input:"]
        }
    }

    try:
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        # result = data.get("response", "").strip()
        # return result if result else input_text[:50]  # fallback if empty
        result = data.get("response", "").strip()

        print("=" * 80)
        print("UTILITY MODEL OUTPUT")
        print(repr(result))
        print("=" * 80)

        return result

    except Exception as e:
        logger.warning(f"Utility LLM call failed ({prompt_file}): {e}")
        return input_text[:50]  # graceful fallback, never breaks the main flow