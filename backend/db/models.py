

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Float, Integer
from sqlalchemy.orm import relationship
from backend.db.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Conversation(Base):
    """
    One chat session. A Policy Assistant conversation and a PDF Chat
    conversation are both stored here, distinguished by 'workspace'.
    """
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False, default="New Chat")
    workspace = Column(String, nullable=False)  # "policy" or "pdf_chat"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One conversation has many messages. Deleting a conversation
    # also deletes its messages (cascade), so we never end up with
    # orphaned messages pointing to a conversation that no longer exists.
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """
    A single question + answer exchange within a conversation.
    Stores both the user's question and the assistant's answer as
    separate rows, so chat history renders in correct order.
    """
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)

    role = Column(String, nullable=False)     # "user" or "assistant"
    content = Column(Text, nullable=False)

    # Only populated for assistant messages — mirrors grounding.py's response
    grounded = Column(Boolean, nullable=True)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    response_time_seconds = Column(Float, nullable=True)
    evidence_json = Column(Text, nullable=True)  # stored as JSON string — see note below

    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", uselist=False, cascade="all, delete-orphan")


class Feedback(Base):
    """
    👍 / 👎 on a specific assistant message. One-to-one with Message
    (a message can have at most one feedback entry — resubmitting
    feedback updates the existing row rather than creating duplicates).
    """
    __tablename__ = "feedback"

    id = Column(String, primary_key=True, default=generate_uuid)
    message_id = Column(String, ForeignKey("messages.id"), nullable=False, unique=True)

    is_helpful = Column(Boolean, nullable=False)  # True = 👍, False = 👎
    created_at = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", back_populates="feedback")