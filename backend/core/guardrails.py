import re
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str | None = None


# Common prompt-injection patterns.
# These are intentionally simple and conservative.
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above\s+instructions",
    r"forget\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?previous\s+instructions",
    r"override\s+(the\s+)?system\s+prompt",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"show\s+(me\s+)?the\s+system\s+prompt",
    r"print\s+(the\s+)?system\s+prompt",
    r"reveal\s+(your\s+)?hidden\s+instructions",
    r"show\s+(your\s+)?hidden\s+instructions",
    r"what\s+are\s+your\s+system\s+instructions",
    r"act\s+as\s+if\s+you\s+have\s+no\s+restrictions",
    r"bypass\s+(your\s+)?(rules|restrictions|safety)",
    r"jailbreak",
]


def check_query_guardrail(question: str) -> GuardrailResult:
    """
    Performs lightweight input validation before the RAG pipeline.

    Returns:
        GuardrailResult(allowed=True)  -> continue normally
        GuardrailResult(allowed=False) -> reject the query
    """

    if not question or not question.strip():
        return GuardrailResult(
            allowed=False,
            reason="Question cannot be empty.",
        )

    normalized = " ".join(question.lower().split())

    # Prevent extremely large input from reaching the pipeline.
    if len(normalized) > 1000:
        return GuardrailResult(
            allowed=False,
            reason="Question is too long.",
        )

    # Detect common prompt-injection attempts.
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            return GuardrailResult(
                allowed=False,
                reason="The request contains an unsafe instruction.",
            )

    return GuardrailResult(allowed=True)