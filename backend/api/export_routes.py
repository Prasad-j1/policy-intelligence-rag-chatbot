from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.repository import conversation_repo, message_repo
from backend.core.export import export_as_txt, export_as_markdown, export_as_pdf
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

_EXPORTERS = {
    "txt": (export_as_txt, "text/plain", "txt"),
    "md": (export_as_markdown, "text/markdown", "md"),
    "pdf": (export_as_pdf, "application/pdf", "pdf"),
}


@router.get("/{conversation_id}/{format}")
def export_conversation(conversation_id: str, format: str, db: Session = Depends(get_db)):
    """
    Exports a full conversation as a downloadable file.
    format must be one of: txt, md, pdf
    """
    if format not in _EXPORTERS:
        raise HTTPException(status_code=400, detail="format must be one of: txt, md, pdf")

    conversation = conversation_repo.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    messages = message_repo.get_messages_for_conversation(db, conversation_id)
    if not messages:
        raise HTTPException(status_code=400, detail="Conversation has no messages to export.")

    export_fn, media_type, extension = _EXPORTERS[format]

    try:
        file_bytes = export_fn(conversation.title, messages)
    except Exception as e:
        logger.error(f"Export failed for conversation '{conversation_id}' as {format}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate export file.")

    filename = f"{conversation.title[:40].strip().replace(' ', '_')}.{extension}"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )