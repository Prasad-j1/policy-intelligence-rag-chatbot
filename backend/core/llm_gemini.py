import time
from urllib import response
# import google.generativeai as genai
from openai import OpenAI
from backend.config import GEMINI_API_KEY, GEMINI_MODEL_NAME, LLM_TEMPERATURE, OLLAMA_MODEL_NAME
from backend.core.prompt_loader import build_grounded_prompt
from backend.utils.logger import get_logger
import traceback


logger = get_logger(__name__)

# Configure the Gemini client once, using the API key from .env
# genai.configure(api_key=GEMINI_API_KEY)
client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://api.morphllm.com/v1",
)

def generate_gemini_answer(workspace_prompt_file: str, context_chunks: list[str], question: str) -> dict:
    """
    Sends a grounded prompt to Gemini and returns the plain-text answer
    along with basic timing info. Same return shape as generate_ollama_answer,
    so routing.py can call either one interchangeably.
    """
    prompt = build_grounded_prompt(workspace_prompt_file, context_chunks, question)

    start_time = time.time()

    try:
        # model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        # response = model.generate_content(
        #     prompt,
        #     generation_config={"temperature": LLM_TEMPERATURE}
        # )
        # answer_text = response.text.strip()
        response = client.chat.completions.create(
            model=GEMINI_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
        )

        answer_text = response.choices[0].message.content.strip()

    except Exception as e:
        # Covers invalid API key, rate limits, network issues, and any
        # other Gemini-side failure — Gemini's SDK doesn't give us clean
        # separate exception types the way "requests" does for Ollama.
        logger.error(f"Gemini API error: {e}")
        return {
            "answer": "The Gemini service is currently unavailable. Please try again shortly.",
            "success": False,
            "provider": "gemini",
            "model": GEMINI_MODEL_NAME,
            "response_time_seconds": round(time.time() - start_time, 2)
        }
    if not answer_text:
        logger.warning("Gemini returned an empty response.")
        return {
            "answer": "The AI model did not return any answer. Please try again.",
            "success": False,
            "provider": "gemini",
            "model": GEMINI_MODEL_NAME,
            "response_time_seconds": round(time.time() - start_time, 2)
        }

    response_time = round(time.time() - start_time, 2)

    return {
        "answer": answer_text,
        "success": True,
        "provider": "gemini",
        "model": GEMINI_MODEL_NAME,
        "response_time_seconds": response_time
    }

def generate_gemini_stream(
    workspace_prompt_file: str,
    context_chunks: list[str],
    question: str,
):
    """
    Streams Gemini responses token-by-token.

    Yields dictionaries compatible with the existing SSE pipeline.
    """

    prompt = build_grounded_prompt(
        workspace_prompt_file,
        context_chunks,
        question,
    )

    start_time = time.time()

    try:
        response = client.chat.completions.create(
        model=GEMINI_MODEL_NAME,
        messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            stream=True,
        )

        full_answer = ""

        for chunk in response:

            if not chunk.choices:
                continue

            delta = getattr(chunk.choices[0].delta, "content", None)

            if delta is None:
                continue

            full_answer += delta

            yield {
                "type": "token",
                "content": delta,
            }

        response_time = round(time.time() - start_time, 2)

        yield {
            "type": "done",
            "answer": full_answer,
            "provider": "gemini",
            "model": GEMINI_MODEL_NAME,
            "response_time_seconds": response_time,
        }

        # model = genai.GenerativeModel(GEMINI_MODEL_NAME)

        # response = model.generate_content(

        #     prompt,

        #     generation_config={
        #         "temperature": LLM_TEMPERATURE
        #     },

        #     stream=True,
        # )

        # full_answer = ""

        # for chunk in response:

        #     token = chunk.text if hasattr(chunk, "text") else ""

        #     if not token:
        #         continue

        #     full_answer += token

        #     yield {
        #         "type": "token",
        #         "content": token
        #     }

        # response_time = round(
        #     time.time() - start_time,
        #     2
        # )

        # yield {
        #     "type": "done",
        #     "answer": full_answer.strip(),
        #     "provider": "gemini",
        #     "model": GEMINI_MODEL_NAME,
        #     "response_time_seconds": response_time,
        # }

    except Exception as e:

        logger.error(f"Gemini streaming error: {e}")
        logger.error(traceback.format_exc())

        yield {
            "type": "error",
            "message": "The Gemini service is currently unavailable. Please try again.",
        }