from sqlalchemy.orm import Session
from backend.db.models import Conversation


def create_conversation(db: Session, workspace: str, title: str = "New Chat") -> Conversation:
    """
    Creates a new conversation row. Called when conversation_id is
    None in a request — i.e. the user is starting a fresh chat.
    """
    conversation = Conversation(workspace=workspace, title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)  # loads the auto-generated id back into the object
    return conversation


def get_conversation(db: Session, conversation_id: str) -> Conversation | None:
    """
    Fetches a single conversation by ID, or None if it doesn't exist.
    """
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def list_conversations(db: Session, workspace: str | None = None) -> list[Conversation]:
    """
    Returns all conversations, optionally filtered by workspace.
    Used for the Chat History sidebar. Ordered newest-updated first.
    """
    query = db.query(Conversation)
    if workspace:
        query = query.filter(Conversation.workspace == workspace)
    return query.order_by(Conversation.updated_at.desc()).all()


def search_conversations(db: Session, search_term: str) -> list[Conversation]:
    """
    Simple title search for the Search Chat History feature.
    Case-insensitive partial match.
    """
    return (
        db.query(Conversation)
        .filter(Conversation.title.ilike(f"%{search_term}%"))
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def update_conversation_title(db: Session, conversation_id: str, title: str) -> Conversation | None:
    """
    Updates a conversation's title. Used by the auto-generated title
    feature (title_prompt.txt) once the first message is answered.
    """
    conversation = get_conversation(db, conversation_id)
    if conversation:
        conversation.title = title
        db.commit()
        db.refresh(conversation)
    return conversation


def delete_conversation(db: Session, conversation_id: str) -> bool:
    """
    Deletes a conversation and all its messages/feedback (cascade,
    as defined in models.py). Returns True if something was deleted.
    """
    conversation = get_conversation(db, conversation_id)
    if conversation:
        db.delete(conversation)
        db.commit()
        return True
    return False