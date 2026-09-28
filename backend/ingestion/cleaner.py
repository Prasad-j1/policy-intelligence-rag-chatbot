import re


# def clean_text(text: str) -> str:
#     """
#     Removes extra whitespace, broken line breaks, and junk characters
#     commonly left behind by PDF text extraction.
#     """
#     text = text.replace("\n", " ")
#     text = re.sub(r"\s+", " ", text)          # collapse multiple spaces
#     text = re.sub(r"[^\x00-\x7F]+", " ", text)  # strip weird unicode artifacts
#     return text.strip()


import re

def clean_text(text: str) -> str:
    # Collapse 3+ line breaks into exactly 2 (a clean paragraph break),
    # but preserve paragraph structure instead of destroying it.
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)  # collapse spaces/tabs, but not newlines
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return text.strip()