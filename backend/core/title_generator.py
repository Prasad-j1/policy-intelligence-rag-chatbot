from backend.core.utility_llm import generate_utility_text


def generate_conversation_title(first_question: str) -> str:
    """
    Generates a short, natural conversation title from the user's
    first question, using title_prompt.txt. Falls back to a
    truncated version of the question if generation fails.
    """
    title = generate_utility_text("title_prompt.txt", first_question, max_tokens=15)
    return title.strip().strip('"')  # strip quotes in case the model adds them despite instructions