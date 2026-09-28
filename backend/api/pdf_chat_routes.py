import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from backend.schemas.chat_schema import UploadResponse
from backend.core.retriever_pdf import build_temp_index, clear_temp_session
from backend.config import UPLOADS_PATH, MAX_UPLOAD_SIZE_MB
from backend.utils.logger import get_logger

from sqlalchemy.orm import Session as DBSession
from backend.schemas.chat_schema import ChatRequest, ChatResponse, EvidenceItem
from backend.core.routing import route_query
from backend.db.session import get_db
from backend.db.repository import conversation_repo, message_repo
# from backend.api._shared import to_evidence_items, make_placeholder_title
from backend.api._shared import to_evidence_items
from backend.core.title_generator import generate_conversation_title
from backend.core.followup_generator import generate_followup_questions
from backend.config import ENABLE_FOLLOWUP_QUESTIONS


from backend.core.suggested_questions import get_suggested_questions
from backend.schemas.chat_schema import SuggestedQuestionsResponse



logger = get_logger(__name__)

router = APIRouter()

MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Accepts a PDF upload, validates it, saves it temporarily, and
    builds a temporary FAISS index scoped to a new session_id.
    """
    # Step 1: Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Step 2: Read into memory once, validate size
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE_MB}MB."
        )
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Step 3: Generate a new session_id and save the file temporarily
    session_id = str(uuid.uuid4())
    Path(UPLOADS_PATH).mkdir(parents=True, exist_ok=True)
    saved_path = Path(UPLOADS_PATH) / f"{session_id}.pdf"

    with open(saved_path, "wb") as f:
        f.write(contents)

    logger.info(f"Saved upload for session '{session_id}': {file.filename}")

    # Step 4: Build the temp index (load, clean, chunk, embed, FAISS)
    try:
        # chunk_count = build_temp_index(session_id, str(saved_path))
        chunk_count = build_temp_index(session_id, str(saved_path), file.filename)

    except ValueError as e:
        # e.g. "No readable text found in the uploaded PDF"
        logger.error(f"Failed to index upload for session '{session_id}': {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Unexpected error indexing upload for session '{session_id}': {e}")
        raise HTTPException(status_code=500, detail="Failed to process the uploaded PDF.")

    finally:
        # The temp index now lives in memory (see retriever_pdf.py);
        # the raw uploaded file on disk is no longer needed after indexing.
        saved_path.unlink(missing_ok=True)

    return UploadResponse(
        session_id=session_id,
        filename=file.filename,
        chunk_count=chunk_count,
        message="PDF uploaded and indexed successfully. Use this session_id to ask questions."
    )


@router.post("/clear/{session_id}")
def clear_workspace(session_id: str):
    """
    Ends a PDF Chat session — deletes the temporary FAISS index,
    chunks, and metadata from memory. Matches the "Clear Workspace"
    button and the "uploading a new PDF ends the old session" rule.
    """
    clear_temp_session(session_id)
    return {"status": "cleared", "session_id": session_id}



def _to_evidence_items(results: list[dict]) -> list[EvidenceItem]:
    """
    Same conversion as policy_routes.py — duplicated here rather than
    imported, since both files are small and independent. If this
    logic needs to change, it must be updated in both places.
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


@router.post("/ask", response_model=ChatResponse)
def ask_pdf_question(request: ChatRequest, db: DBSession = Depends(get_db)) -> ChatResponse:
    """
    PDF Chat endpoint. Requires session_id (from a prior /upload call)
    to know which temporary document index to search.
    """
    if not request.session_id:
        raise HTTPException(
            status_code=400,
            detail="session_id is required for PDF Chat. Upload a PDF first via /pdf_chat/upload."
        )

    logger.info(f"PDF Chat question received (session={request.session_id}): '{request.question}'")

    # Step 1: Resolve the conversation
    if request.conversation_id:
        conversation = conversation_repo.get_conversation(db, request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")
    else:
        # title = " ".join(request.question.strip().split()[:6])
        # title = make_placeholder_title(request.question)
        title = generate_conversation_title(request.question)
        conversation = conversation_repo.create_conversation(db, workspace="pdf_chat", title=title)

    # Step 2: Save the user's question
    message_repo.add_user_message(db, conversation.id, request.question)

    # Step 3: Run the RAG pipeline
    try:
        result = route_query(
            workspace="pdf_chat",
            question=request.question,
            session_id=request.session_id,
            provider=request.provider
        )
        
    except ValueError as e:
        # Raised by routing.py/retriever_pdf.py if the session doesn't exist
        logger.error(f"PDF Chat session error: {e}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Unexpected error in PDF Chat: {e}")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while processing your question. Please try again."
        )

    # Step 4: Save the assistant's answer
    # evidence_items = _to_evidence_items(result["evidence"])
    evidence_items = to_evidence_items(result["evidence"])
    # followups = generate_followup_questions(request.question, result["answer"])
    followups = generate_followup_questions(request.question, result["answer"]) if ENABLE_FOLLOWUP_QUESTIONS else []



    message_repo.add_assistant_message(
        db,
        conversation_id=conversation.id,
        content=result["answer"],
        grounded=result["grounded"],
        provider=result["provider"],
        model=result["model"],
        response_time_seconds=result["response_time_seconds"],
        evidence=[item.model_dump() for item in evidence_items]
    )

    return ChatResponse(
        answer=result["answer"],
        grounded=result["grounded"],
        provider=result["provider"],
        model=result["model"],
        evidence=evidence_items,
        retriever_time_seconds=result["retriever_time_seconds"],
        response_time_seconds=result["response_time_seconds"],
        conversation_id=conversation.id,
        followup_questions=followups   # ← add this line
    )



@router.get("/suggested-questions", response_model=SuggestedQuestionsResponse)
def suggested_questions():
    return SuggestedQuestionsResponse(workspace="pdf_chat", questions=get_suggested_questions("pdf_chat"))