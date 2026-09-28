from sqlalchemy.orm import Session
from backend.db.models import Feedback


def submit_feedback(db: Session, message_id: str, is_helpful: bool) -> Feedback:
    """
    Records 👍/👎 on a message. Since Feedback.message_id is unique
    (see models.py), resubmitting feedback on the same message updates
    the existing row instead of creating a duplicate.
    """
    existing = db.query(Feedback).filter(Feedback.message_id == message_id).first()

    if existing:
        existing.is_helpful = is_helpful
        db.commit()
        db.refresh(existing)
        return existing

    feedback = Feedback(message_id=message_id, is_helpful=is_helpful)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_feedback_for_message(db: Session, message_id: str) -> Feedback | None:
    """
    Fetches feedback for a specific message, if any exists.
    """
    return db.query(Feedback).filter(Feedback.message_id == message_id).first()