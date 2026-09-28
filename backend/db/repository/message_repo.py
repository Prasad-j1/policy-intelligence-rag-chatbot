import json
from sqlalchemy.orm import Session
from backend.db.models import Message


def add_user_message(db: Session, conversation_id: str, content: str) -> Message:
    """
    Stores the user's question as a message row.
    """
    message = Message(
        conversation_id=conversation_id,
        role="user",
        content=content
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def add_assistant_message(
    db: Session,
    conversation_id: str,
    content: str,
    grounded: bool,
    provider: str | None,
    model: str | None,
    response_time_seconds: float,
    evidence: list[dict]
) -> Message:
    """
    Stores the assistant's answer, along with all the Developer Mode /
    Evidence Panel metadata that came back from grounding.py.
    Evidence is serialized to a JSON string, since evidence_json is a
    Text column, not a separate table (see models.py for why).
    """
    message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=content,
        grounded=grounded,
        provider=provider,
        model=model,
        response_time_seconds=response_time_seconds,
        evidence_json=json.dumps(evidence)
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_messages_for_conversation(db: Session, conversation_id: str) -> list[dict]:
    """
    Returns all messages in a conversation, ordered oldest-first
    (correct chat display order). Evidence is deserialized back
    into a real list before returning, so callers never deal with
    raw JSON strings.
    """
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    result = []
    for m in messages:
        result.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "grounded": m.grounded,
            "provider": m.provider,
            "model": m.model,
            "response_time_seconds": m.response_time_seconds,
            "evidence": json.loads(m.evidence_json) if m.evidence_json else [],
            "created_at": m.created_at.isoformat()
        })
    return result