from backend.core.utility_llm import generate_utility_text


def generate_followup_questions(question: str, answer: str) -> list[str]:
    """
    Generates 2-3 short follow-up questions based on the last
    question + answer, using followup_prompt.txt. Falls back to
    an empty list if generation fails — follow-ups are a nice-to-have,
    never a reason to break the main response.
    """
    input_text = f"Question: {question}\nAnswer: {answer}"

    result = generate_utility_text("followup_prompt.txt", input_text, max_tokens=150)

    if not result:
        return []

    # followup_prompt.txt instructs one question per line, no numbering
    questions = []

    for line in result.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Stop if model starts a fake conversation
        if line.lower().startswith("user:"):
            break
        if line.lower().startswith("assistant:"):
            break
        # Remove bullets/numbers
        line = line.lstrip("-•1234567890. ").strip()
        # Keep only actual questions
        if line.endswith("?"):
            questions.append(line)

    return questions[:3]  # hard cap at 3, even if the model returns more