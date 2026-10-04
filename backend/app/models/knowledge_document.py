"""
Knowledge Document model — UdyamSetu AI RAG System

Represents documents ingested into the AI knowledge base for
Retrieval-Augmented Generation (RAG). Each document is split into
chunks, each with an embedding vector stored for similarity search.
"""

import enum

from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class KnowledgeCategory(str, enum.Enum):
    """Categories of knowledge documents."""
    REGULATORY = "regulatory"
    SCHEME = "scheme"
    COMPLIANCE = "compliance"
    PROCEDURE = "procedure"
    FAQ = "faq"
    POLICY = "policy"
    GUIDELINE = "guideline"
    NOTIFICATION = "notification"


class ProcessingStatus(str, enum.Enum):
    """Processing pipeline state."""
    PENDING = "pending"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


class KnowledgeDocument(BaseModel):
    """
    A source document ingested into the RAG knowledge base.
    Tracks metadata, processing status, and owns its child chunks.
    """
    __tablename__ = "knowledge_documents"

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(30),
        default=KnowledgeCategory.REGULATORY.value,
        nullable=False,
        index=True,
    )

    # Processing metadata
    processing_status: Mapped[str] = mapped_column(
        String(20),
        default=ProcessingStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Document metadata
    metadata_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Extra metadata: author, date, jurisdiction, applicable_states, etc.",
    )

    # Relationships
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self):
        data = {col.name: getattr(self, col.name) for col in self.__table__.columns}
        if "chunks" in self.__dict__:
            data["chunk_count"] = len(self.chunks)
        return data


class KnowledgeChunk(BaseModel):
    """
    A text chunk from a knowledge document, with its embedding vector
    stored as a JSON array (SQLite) or pgvector column (PostgreSQL).
    """
    __tablename__ = "knowledge_chunks"

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Embedding vector stored as JSON array for SQLite compatibility
    # In production with PostgreSQL + pgvector, this would be a Vector column
    embedding: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Embedding vector stored as JSON array of floats.",
    )
    embedding_model: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    embedding_dimensions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Chunk metadata
    metadata_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Positional metadata: section_title, page_number, etc.",
    )

    # Relationship back to parent document
    document: Mapped["KnowledgeDocument"] = relationship(
        "KnowledgeDocument",
        back_populates="chunks",
    )

    def to_dict(self):
        data = {col.name: getattr(self, col.name) for col in self.__table__.columns}
        # Don't serialize the raw embedding vector by default (too large)
        data.pop("embedding", None)
        return data
