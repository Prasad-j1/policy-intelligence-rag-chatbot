from pathlib import Path
from backend.config import PROMPTS_PATH


def load_prompt(filename: str) -> str:
    """
    Reads a single prompt file from the prompts/ directory.
    Example: load_prompt("system_prompt.txt")
    """

    path = Path(PROMPTS_PATH) / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def build_grounded_prompt(
    workspace_prompt_file: str,
    context_chunks: list[str],
    question: str,
) -> str:

    system_prompt = load_prompt("system_prompt.txt")

    workspace_prompt = load_prompt(workspace_prompt_file)

    context = "\n\n".join(
        f"Chunk {i+1}:\n{chunk}"
        for i, chunk in enumerate(context_chunks)
    )

    return (
        f"{system_prompt}\n\n"
        f"{workspace_prompt}\n\n"
        "==============================\n"
        "RETRIEVED CONTEXT\n"
        "==============================\n\n"
        f"{context}\n\n"
        "==============================\n"
        "USER QUESTION\n"
        "==============================\n\n"
        f"{question}\n\n"
        "==============================\n"
        "ANSWER\n"
        "==============================\n"
    )