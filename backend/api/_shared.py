# This creates one shared helper file that both policy_routes.py and pdf_chat_routes.py import from, instead of each having their own copy of the same logic. 
# If either piece of logic ever needs to change, it changes in exactly one place.

from backend.schemas.chat_schema import EvidenceItem

from backend.core.title_generator import generate_conversation_title

def to_evidence_items(results: list[dict]) -> list[EvidenceItem]:
    """
    Converts retriever.py's / retriever_pdf.py's raw internal result
    shape into the clean EvidenceItem schema promised by the API.
    Shared by policy_routes.py and pdf_chat_routes.py so this
    conversion logic exists in exactly one place.
    """
    evidence_items = []
    for r in results:
        metadata = r["metadata"]
        evidence_items.append(EvidenceItem(
            source=metadata["source"],
            page=metadata["page"],
            section=metadata["section"],
            similarity_score=r["similarity_score"],
            chunk_id=metadata["chunk_id"]
        ))
    return evidence_items


# def make_placeholder_title(question: str) -> str:
#     """
#     Temporary title generation: truncates the first question to a
#     short title. Shared by both workspaces. Will be replaced once
#     title_prompt.txt is wired up to a real LLM call.
#     """
#     words = question.strip().split()
#     title = " ".join(words[:6])
#     return title if len(words) <= 6 else title + "..."