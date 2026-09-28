from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.api._shared import to_evidence_items
from backend.schemas.chat_schema import ChatRequest, ChatResponse, EvidenceItem
from backend.core.routing import route_query
from backend.db.session import get_db
from backend.db.repository import conversation_repo, message_repo
from backend.utils.logger import get_logger
# from backend.api._shared import to_evidence_items, make_placeholder_title
# from backend.api._shared import to_evidence_items
from backend.core.title_generator import generate_conversation_title
from backend.core.followup_generator import generate_followup_questions
from backend.config import ENABLE_FOLLOWUP_QUESTIONS

from backend.core.suggested_questions import get_suggested_questions
from backend.schemas.chat_schema import SuggestedQuestionsResponse

from fastapi.responses import StreamingResponse
import json
from backend.core.routing import (
    route_query,
    route_query_stream
)


logger = get_logger(__name__)

router = APIRouter()



@router.post("/ask")
def ask_policy_question(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """
    Main Policy Assistant endpoint. Creates or continues a conversation,
    runs the full RAG pipeline, and persists both the question and answer.
    """
    logger.info(f"Policy Assistant question received: '{request.question}'")

    # Step 1: Resolve the conversation — create new, or continue existing
    if request.conversation_id:
        conversation = conversation_repo.get_conversation(db, request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")
    else:
        title = generate_conversation_title(request.question)
        conversation = conversation_repo.create_conversation(db, workspace="policy", title=title)

    # Step 2: Save the user's question
    message_repo.add_user_message(db, conversation.id, request.question)

    # Step 3: Run the RAG pipeline
    try:
        result = route_query(workspace="policy", question=request.question,provider=request.provider,)

    except FileNotFoundError as e:
        logger.error(f"Index not found: {e}")
        raise HTTPException(
            status_code=503,
            detail="The knowledge base index is not ready. Please contact the administrator."
        )

    except Exception as e:
        logger.error(f"Unexpected error in Policy Assistant: {e}")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while processing your question. Please try again."
        )

    # Step 4: Save the assistant's answer
    evidence_items = to_evidence_items(result["evidence"])  # flatten once, use everywhere
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
        evidence=[item.model_dump() for item in evidence_items]  # flat dicts, matches EvidenceItem shape
    )
    print("=========================================================================================================")
    print(type(evidence_items[0]))
    print(EvidenceItem)
    print(type(evidence_items[0]) is EvidenceItem)
    print("=========================================================================================================")

    response = ChatResponse(
        answer=result["answer"],
        grounded=result["grounded"],
        provider=result["provider"],
        model=result["model"],
        evidence=evidence_items,
        retriever_time_seconds=result["retriever_time_seconds"],
        response_time_seconds=result["response_time_seconds"],
        conversation_id=conversation.id,
        followup_questions=followups
    )

    print(response.model_dump())


    return response
@router.post("/stream")
def stream_policy_answer(
    request: ChatRequest,
    db: Session = Depends(get_db)
):

    # ----------------------------------
    # Resolve conversation
    # ----------------------------------

    if request.conversation_id:

        conversation = conversation_repo.get_conversation(
            db,
            request.conversation_id
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found."
            )

    else:

        title = generate_conversation_title(
            request.question
        )

        conversation = conversation_repo.create_conversation(
            db,
            workspace="policy",
            title=title
        )
    conversation_id = conversation.id

    # ----------------------------------
    # Save user message
    # ----------------------------------

    message_repo.add_user_message(
        db,
        conversation_id,
        request.question
    )

    def event_generator():

        answer = ""

        final_event = None

        try:

            for event in route_query_stream(
                workspace="policy",
                question=request.question,
                provider=request.provider,
            ):

                # -------------------------
                # Stream tokens
                # -------------------------

                if event["type"] == "token":

                    answer += event["content"]

                    yield f"data: {json.dumps(event)}\n\n"

                # -------------------------
                # Error
                # -------------------------

                elif event["type"] == "error":

                    yield f"data: {json.dumps(event)}\n\n"

                    return

                # -------------------------
                # Final metadata
                # -------------------------

                elif event["type"] == "done":

                    final_event = event

            # --------------------------------
            # Convert evidence
            # --------------------------------

            evidence_items = to_evidence_items(
                final_event["evidence"]
            )

            # --------------------------------
            # Follow-up questions
            # --------------------------------

            followups = (
                generate_followup_questions(
                    request.question,
                    answer
                )
                if ENABLE_FOLLOWUP_QUESTIONS
                else []
            )

            # --------------------------------
            # Save assistant message
            # --------------------------------

            message_repo.add_assistant_message(
                db,
                conversation_id=conversation_id,
                content=answer,
                grounded=final_event["grounded"],
                provider=final_event["provider"],
                model=final_event["model"],
                response_time_seconds=final_event["response_time_seconds"],
                evidence=[
                    item.model_dump()
                    for item in evidence_items
                ]
            )

            # --------------------------------
            # Enrich final event
            # --------------------------------

            final_event["conversation_id"] = conversation_id

            final_event["followup_questions"] = followups

            final_event["evidence"] = [
                item.model_dump()
                for item in evidence_items
            ]

            # --------------------------------
            # Send final packet
            # --------------------------------

            yield f"data: {json.dumps(final_event)}\n\n"

        except Exception as e:

            logger.exception(e)

            yield (
                f"data: "
                f"{json.dumps({'type':'error','message':str(e)})}"
                "\n\n"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.get("/suggested-questions", response_model=SuggestedQuestionsResponse)
def suggested_questions():
    return SuggestedQuestionsResponse(workspace="policy", questions=get_suggested_questions("policy"))