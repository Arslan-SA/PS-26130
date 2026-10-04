"""
Vector Store — UdyamSetu AI RAG System

Provides similarity search over knowledge chunk embeddings.
Uses cosine similarity computed in Python for SQLite compatibility.
In production with PostgreSQL + pgvector, this would use native
vector distance operators for much faster queries.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge_document import KnowledgeChunk, KnowledgeDocument

logger = logging.getLogger("udyamsetu.vector_store")


@dataclass
class SearchResult:
    """A single similarity search result with score and metadata."""
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    similarity_score: float
    chunk_index: int
    category: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "content": self.content,
            "similarity_score": round(self.similarity_score, 4),
            "chunk_index": self.chunk_index,
            "category": self.category,
            "metadata": self.metadata,
        }


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    Returns a value in [-1, 1] where 1 means identical direction.
    """
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot_product / (norm_a * norm_b)


async def similarity_search(
    db: AsyncSession,
    query_embedding: List[float],
    *,
    top_k: int = 5,
    min_score: float = 0.3,
    category_filter: Optional[str] = None,
) -> List[SearchResult]:
    """
    Find the top-k most similar knowledge chunks for a query embedding.

    For SQLite: loads all chunk embeddings and computes similarity in-memory.
    For PostgreSQL + pgvector: would use ``<=>`` cosine distance operator.
    """
    # Build query
    stmt = (
        select(KnowledgeChunk)
        .join(KnowledgeDocument)
        .where(KnowledgeChunk.embedding.isnot(None))
        .where(KnowledgeDocument.is_active == True)
    )

    if category_filter:
        stmt = stmt.where(KnowledgeDocument.category == category_filter)

    # Include parent document for title & category
    stmt = stmt.options(selectinload(KnowledgeChunk.document))

    result = await db.execute(stmt)
    chunks = result.scalars().all()

    if not chunks:
        return []

    # Compute similarities
    scored_chunks: List[Tuple[float, KnowledgeChunk]] = []
    for chunk in chunks:
        embedding = chunk.embedding
        if not embedding or not isinstance(embedding, list):
            continue

        score = cosine_similarity(query_embedding, embedding)
        if score >= min_score:
            scored_chunks.append((score, chunk))

    # Sort by similarity (descending) and take top-k
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_results = scored_chunks[:top_k]

    results = []
    for score, chunk in top_results:
        doc = chunk.document
        results.append(SearchResult(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=doc.title if doc else "Unknown",
            content=chunk.content,
            similarity_score=score,
            chunk_index=chunk.chunk_index,
            category=doc.category if doc else "",
            metadata=chunk.metadata_json or {},
        ))

    logger.debug(
        f"Similarity search: {len(results)} results "
        f"(top score: {results[0].similarity_score:.4f})" if results else
        "Similarity search: 0 results"
    )

    return results


async def get_knowledge_stats(db: AsyncSession) -> Dict[str, Any]:
    """Return statistics about the knowledge base."""
    from sqlalchemy import func

    doc_count = await db.execute(
        select(func.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.is_active == True
        )
    )
    chunk_count = await db.execute(
        select(func.count(KnowledgeChunk.id))
    )
    embedded_count = await db.execute(
        select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.embedding.isnot(None)
        )
    )

    return {
        "total_documents": doc_count.scalar() or 0,
        "total_chunks": chunk_count.scalar() or 0,
        "embedded_chunks": embedded_count.scalar() or 0,
    }
