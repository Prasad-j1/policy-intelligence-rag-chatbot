from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.schemas.chat_schema import FeedbackRequest, FeedbackResponse
from backend.db.session import get_db
from backend.db.repository import feedback_repo, message_repo
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """
    Records or updates 👍/👎 feedback on a specific assistant message.
    Resubmitting feedback on the same message updates the existing
    entry (handled inside feedback_repo.submit_feedback).
    """
    feedback = feedback_repo.submit_feedback(
        db,
        message_id=request.message_id,
        is_helpful=request.is_helpful
    )

    logger.info(f"Feedback recorded: message_id={request.message_id}, helpful={request.is_helpful}")

    return FeedbackResponse(
        id=feedback.id,
        message_id=feedback.message_id,
        is_helpful=feedback.is_helpful
    )


@router.get("/{message_id}", response_model=FeedbackResponse)
def get_feedback(message_id: str, db: Session = Depends(get_db)):
    """
    Fetches existing feedback for a message, if any — useful for the
    frontend to show which button (👍/👎) should appear already selected.
    """
    feedback = feedback_repo.get_feedback_for_message(db, message_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="No feedback found for this message.")

    return FeedbackResponse(
        id=feedback.id,
        message_id=feedback.message_id,
        is_helpful=feedback.is_helpful
    )