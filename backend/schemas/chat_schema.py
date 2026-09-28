from pydantic import BaseModel, Field
from typing import Optional

from datetime import datetime

from pydantic import BaseModel, computed_field

class EvidenceItem(BaseModel):
    source: str
    page: int
    section: str
    similarity_score: float
    chunk_id: str

    @computed_field
    @property
    def citation_text(self) -> str:
        return f"Source: {self.source}, Page: {self.page}, Section: {self.section}"

class ChatRequest(BaseModel):
    """
    What the frontend sends when a user asks a question.
    Used by both Policy Assistant and PDF Chat endpoints.
    """
    question: str = Field(..., min_length=1, max_length=1000)

    conversation_id: Optional[str] = Field(default=None)

    session_id: Optional[str] = Field(default=None)

    provider: str = Field(
        default="ollama",
        description="LLM provider to use: ollama or gemini"
    )


class ChatResponse(BaseModel):
    """
    What the backend sends back after answering a question.
    Matches the shape returned by grounding.generate_grounded_response(),
    reformatted into a clean API contract.
    """
    answer: str
    grounded: bool
    provider: Optional[str] = None
    model: Optional[str] = None
    evidence: list[EvidenceItem] = []
    retriever_time_seconds: float
    response_time_seconds: float
    conversation_id: Optional[str] = None
    followup_questions: list[str] = []   # ← add this line




class ConversationSummary(BaseModel):
    """
    A lightweight representation of a conversation, used in the
    Chat History sidebar list (no messages included — just enough
    to display and let the user pick one).
    """
    id: str
    title: str
    workspace: str
    created_at: datetime
    updated_at: datetime


class MessageDetail(BaseModel):
    """
    A single message within a conversation, including all Developer
    Mode / Evidence Panel metadata for assistant messages.
    """
    id: str
    role: str
    content: str
    grounded: Optional[bool] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    response_time_seconds: Optional[float] = None
    evidence: list[EvidenceItem] = []
    created_at: datetime


class ConversationDetail(BaseModel):
    """
    Full conversation view — used when a user opens a specific chat
    from history. Includes all messages in order.
    """
    id: str
    title: str
    workspace: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageDetail]

class FeedbackRequest(BaseModel):
    """
    Sent when a user clicks 👍 or 👎 on an assistant message.
    """
    message_id: str = Field(..., description="The ID of the assistant message being rated")
    is_helpful: bool = Field(..., description="True for 👍 Helpful, False for 👎 Not Helpful")


class FeedbackResponse(BaseModel):
    """
    Confirms feedback was recorded.
    """
    id: str
    message_id: str
    is_helpful: bool


class UploadResponse(BaseModel):
    """
    Returned after a PDF is successfully uploaded and indexed.
    session_id must be included in all subsequent /pdf_chat/ask calls.
    """
    session_id: str
    filename: str
    chunk_count: int
    message: str

# class ChatResponse(BaseModel):
#     answer: str
#     grounded: bool
#     provider: Optional[str] = None
#     model: Optional[str] = None
#     evidence: list[EvidenceItem] = []
#     retriever_time_seconds: float
#     response_time_seconds: float
#     conversation_id: Optional[str] = None
#     followup_questions: list[str] = []   # ← add this line


class SuggestedQuestionsResponse(BaseModel):
    workspace: str
    questions: list[str]



class RenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)