import os
from datetime import datetime
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def _format_conversation_as_text(title: str, messages: list[dict]) -> str:
    """
    Builds a plain-text representation of a conversation.
    Shared by TXT and Markdown exporters.
    """
    lines = [
        f"Conversation: {title}",
        f"Exported: {datetime.utcnow().isoformat()}",
        "=" * 50,
        ""
    ]

    for msg in messages:
        speaker = "You" if msg["role"] == "user" else "Assistant"

        lines.append(f"{speaker}:")
        lines.append(msg["content"])

        if msg["role"] == "assistant" and msg.get("evidence"):
            lines.append("")
            lines.append("Sources:")

            for ev in msg["evidence"]:
                filename = os.path.basename(ev["source"])
                lines.append(
                    f"  - {filename} (Page {ev['page']}, {ev['section']})"
                )

        lines.append("")

    return "\n".join(lines)


def export_as_txt(title: str, messages: list[dict]) -> bytes:
    return _format_conversation_as_text(title, messages).encode("utf-8")


def export_as_markdown(title: str, messages: list[dict]) -> bytes:
    lines = [
        f"# {title}",
        f"*Exported: {datetime.utcnow().isoformat()}*",
        ""
    ]

    for msg in messages:
        speaker = "**You**" if msg["role"] == "user" else "**Assistant**"

        lines.append(speaker)
        lines.append("")
        lines.append(msg["content"])
        lines.append("")

        if msg["role"] == "assistant" and msg.get("evidence"):
            lines.append("> **Sources:**")

            for ev in msg["evidence"]:
                filename = os.path.basename(ev["source"])
                lines.append(
                    f"> - {filename} (Page {ev['page']}, {ev['section']})"
                )

            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines).encode("utf-8")


def export_as_pdf(title: str, messages: list[dict]) -> bytes:
    """
    Exports conversation as PDF.
    Compatible with pyfpdf (fpdf 1.7.2).
    """

    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    usable_width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("Arial", "B", 16)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(usable_width, 10, title)

    pdf.set_font("Arial", "", 9)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        usable_width,
        6,
        f"Exported: {datetime.utcnow().isoformat()}"
    )

    pdf.ln(4)

    for msg in messages:

        speaker = "You" if msg["role"] == "user" else "Assistant"

        pdf.set_font("Arial", "B", 11)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(usable_width, 7, speaker)

        pdf.set_font("Arial", "", 10)

        safe_content = (
            str(msg["content"])
            .encode("latin-1", "ignore")
            .decode("latin-1")
        )

        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            usable_width,
            6,
            safe_content
        )

        if msg["role"] == "assistant" and msg.get("evidence"):

            pdf.ln(1)

            pdf.set_font("Arial", "I", 8)

            for ev in msg["evidence"]:

                filename = os.path.basename(ev["source"])

                source_line = (
                    f"Source: {filename} "
                    f"(Page {ev['page']}, {ev['section']})"
                )

                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(
                    usable_width,
                    5,
                    source_line
                )

        pdf.ln(5)

    pdf_bytes = pdf.output(dest="S")

    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1")
    else:
        pdf_bytes = bytes(pdf_bytes)

    return pdf_bytes