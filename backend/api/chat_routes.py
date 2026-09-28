from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from backend.schemas.chat_schema import ConversationSummary, ConversationDetail, MessageDetail, EvidenceItem
from backend.db.session import get_db
from backend.db.repository import conversation_repo, message_repo
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationSummary])
def get_all_conversations(
    workspace: Optional[str] = Query(default=None, description="Filter by 'policy' or 'pdf_chat'"),
    db: Session = Depends(get_db)
):
    """
    Returns all conversations for the Chat History sidebar.
    Optionally filtered by workspace.
    """
    conversations = conversation_repo.list_conversations(db, workspace=workspace)
    return conversations


@router.get("/conversations/search", response_model=list[ConversationSummary])
def search_conversations(
    q: str = Query(..., min_length=1, description="Search term to match against conversation titles"),
    db: Session = Depends(get_db)
):
    """
    Search Chat History feature — case-insensitive partial title match.
    """
    results = conversation_repo.search_conversations(db, search_term=q)
    return results


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation_detail(conversation_id: str, db: Session = Depends(get_db)):
    """
    Returns a full conversation with all its messages in order.
    Used when the user clicks into a specific chat from history.
    """
    conversation = conversation_repo.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    messages = message_repo.get_messages_for_conversation(db, conversation_id)

    message_details = [
        MessageDetail(
            id=m["id"],
            role=m["role"],
            content=m["content"],
            grounded=m["grounded"],
            provider=m["provider"],
            model=m["model"],
            response_time_seconds=m["response_time_seconds"],
            evidence=[EvidenceItem(**e) for e in m["evidence"]],
            created_at=m["created_at"]
        )
        for m in messages
    ]

    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        workspace=conversation.workspace,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=message_details
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """
    Deletes a conversation and all its messages/feedback (cascade).
    """
    deleted = conversation_repo.delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"status": "deleted", "conversation_id": conversation_id}

from backend.schemas.chat_schema import RenameRequest

@router.patch("/conversations/{conversation_id}/title", response_model=ConversationSummary)
def rename_conversation(conversation_id: str, request: RenameRequest, db: Session = Depends(get_db)):
    """
    Renames a conversation. Used by the sidebar's rename action.
    """
    conversation = conversation_repo.update_conversation_title(db, conversation_id, request.title)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation