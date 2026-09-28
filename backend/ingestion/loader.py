import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict
import re

from typing import List, Dict
import fitz  # PyMuPDF

def load_pdf(file_path: str) -> List[Dict]:
    """
    Opens a single PDF and extracts text page by page, along with
    any detected section headings (based on font size).
    Returns: [{ "page": 1, "text": "...", "headings": [...] }, ...]
    """
    doc = fitz.open(file_path)
    pages = []

    for page_number, page in enumerate(doc, start=1):
        text = page.get_text()
        headings = _extract_headings(page)

        pages.append({
            "page": page_number,
            "text": text,
            "headings": headings   # e.g. ["Maternity Leave", "Paternity Leave"]
        })

    doc.close()
    return pages


def _extract_headings(page) -> List[str]:
    """
    Detects section headings using two signals, in priority order:
    1. Text matching "Section N: ..." pattern (used consistently in
       these policy PDFs) — highest confidence.
    2. Bold, standalone lines under 6 words that aren't purely numeric
       (filters out table cells like "18", "Working", "Days").

    This is a heuristic tuned to this document's actual formatting
    (confirmed via debug_headings.py), not a universal PDF parser.
    """
    blocks = page.get_text("dict")["blocks"]
    headings = []

    for block in blocks:
        for line in block.get("lines", []):
            # Reassemble the full line text from its spans, since
            # headings can be split across multiple spans (e.g. "Section" + " 1: Purpose")
            line_text = "".join(span["text"] for span in line.get("spans", [])).strip()
            if not line_text:
                continue

            is_bold = any("Bold" in span["font"] for span in line.get("spans", []))

            # Priority 1: explicit "Section N:" pattern
            if re.match(r"^Section\s+\d+\s*:", line_text):
                headings.append(line_text)
                continue

            # Priority 2: bold, short, standalone line — likely a heading,
            # not a table cell (table cells are usually single short words
            # or pure numbers, so require at least 2 words and some letters)
            word_count = len(line_text.split())
            has_letters = bool(re.search(r"[A-Za-z]{3,}", line_text))

            if is_bold and 2 <= word_count <= 6 and has_letters and line_text.endswith(":"):
                headings.append(line_text.rstrip(":"))

    return headings

def load_knowledge_base(folder_path: str) -> List[Dict]:
    """
    Loads every PDF inside the knowledge_base folder.
    Returns a list of dicts, one per PDF, each containing its pages.
    [{ "source": "Leave Policy.pdf", "pages": [...] }, ...]
    """
    folder = Path(folder_path)
    all_documents = []

    for pdf_file in folder.glob("*.pdf"):
        pages = load_pdf(str(pdf_file))
        all_documents.append({
            "source": pdf_file.name,
            "pages": pages
        })

    return all_documents