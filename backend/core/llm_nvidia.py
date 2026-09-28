import time
from openai import OpenAI

from backend.config import (
    NVIDIA_API_KEY,
    NVIDIA_MODEL_NAME,
    LLM_TEMPERATURE,
)
from backend.core.prompt_loader import build_grounded_prompt
from backend.utils.logger import get_logger

logger = get_logger(__name__)


client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
)


def generate_nvidia_answer(
    workspace_prompt_file: str,
    context_chunks: list[str],
    question: str,
) -> dict:

    prompt = build_grounded_prompt(
        workspace_prompt_file,
        context_chunks,
        question,
    )

    start_time = time.time()

    try:
        response = client.chat.completions.create(
            model=NVIDIA_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=LLM_TEMPERATURE,
            top_p=0.95,
            max_tokens=500,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            },
        )

        answer_text = response.choices[0].message.content

        if not answer_text:
            raise ValueError("NVIDIA returned an empty response.")

        return {
            "answer": answer_text.strip(),
            "success": True,
            "provider": "nvidia",
            "model": NVIDIA_MODEL_NAME,
            "response_time_seconds": round(
                time.time() - start_time,
                2,
            ),
        }

    except Exception as e:

        logger.error(f"NVIDIA API error: {e}")

        return {
            "answer": "The NVIDIA AI service is currently unavailable. Please try again shortly.",
            "success": False,
            "provider": "nvidia",
            "model": NVIDIA_MODEL_NAME,
            "response_time_seconds": round(
                time.time() - start_time,
                2,
            ),
        }


def generate_nvidia_stream(
    workspace_prompt_file: str,
    context_chunks: list[str],
    question: str,
):

    prompt = build_grounded_prompt(
        workspace_prompt_file,
        context_chunks,
        question,
    )

    start_time = time.time()
    full_answer = ""

    try:

        completion = client.chat.completions.create(
            model=NVIDIA_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=LLM_TEMPERATURE,
            top_p=0.95,
            max_tokens=500,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            },
            stream=True,
        )

        for chunk in completion:

            if not chunk.choices:
                continue

            content = chunk.choices[0].delta.content

            if not content:
                continue

            full_answer += content

            yield {
                "type": "token",
                "content": content,
            }

        yield {
            "type": "done",
            "answer": full_answer.strip(),
            "provider": "nvidia",
            "model": NVIDIA_MODEL_NAME,
            "response_time_seconds": round(
                time.time() - start_time,
                2,
            ),
        }

    except Exception as e:

        logger.error(f"NVIDIA streaming error: {e}")

        yield {
            "type": "error",
            "message": "The NVIDIA AI service is currently unavailable. Please try again.",
        }