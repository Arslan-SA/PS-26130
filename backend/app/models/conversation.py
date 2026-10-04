"""
AI Conversation & Message domain models — UdyamSetu AI

Persists chat history, role-tagged messages, source citations, and
token-usage metadata for the AI assistant feature.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, generate_uuid, utc_now


class ConversationStatus(str, enum.Enum):
    """Lifecycle state of a conversation."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Conversation(BaseModel):
    """
    A chat conversation between a user and the UdyamSetu AI assistant.
    Each conversation stores its title, context scope, and an ordered
    sequence of messages.
    """
    __tablename__ = "conversations"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        default="New Conversation",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=ConversationStatus.ACTIVE.value,
        nullable=False,
    )

    # Context scope — optionally ties conversation to a business
    business_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("businesses.id"),
        nullable=True,
        index=True,
    )

    # Conversation-level metadata
    context_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="E.g. 'approvals', 'compliance', 'schemes', 'general'",
    )
    total_messages: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_tokens_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.sequence_number",
        lazy="selectin",
    )

    def to_dict(self):
        data = {col.name: getattr(self, col.name) for col in self.__table__.columns}
        # Safely serialize messages if loaded
        if "messages" in self.__dict__:
            data["messages"] = [m.to_dict() for m in self.messages]
        return data

    def to_summary_dict(self):
        """Lightweight summary without full message history."""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "context_type": self.context_type,
            "total_messages": self.total_messages,
            "total_tokens_used": self.total_tokens_used,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MessageRole(str, enum.Enum):
    """Role of the message sender."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ConversationMessage(BaseModel):
    """
    A single message within a conversation.
    Tracks role, content, token usage, source citations, and AI model metadata.
    """
    __tablename__ = "conversation_messages"

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    # AI response metadata
    model_used: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    provider_used: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # RAG citation data
    sources: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        doc="List of source documents/chunks used for RAG grounding.",
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Confidence score for RAG-grounded responses (0.0–1.0).",
    )

    # Feedback tracking
    user_rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="User feedback: 1 (thumbs down) or 5 (thumbs up).",
    )

    # Relationship back to conversation
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    def to_dict(self):
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}
