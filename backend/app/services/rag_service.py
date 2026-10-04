"""
RAG (Retrieval-Augmented Generation) Service — UdyamSetu AI

Orchestrates the full RAG pipeline:
1. Embed the user query
2. Retrieve relevant knowledge chunks via vector similarity
3. Augment the system prompt with retrieved context
4. Generate a grounded response with source citations
5. Optionally integrate platform context (business profile, compliance status, etc.)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, ConversationMessage
from app.models.knowledge_document import KnowledgeDocument
from app.services.ai_service import (
    AIResponse,
    ChatMessage,
    MessageRole,
    get_ai_provider,
    UDYAMSETU_SYSTEM_PROMPT,
)
from app.services.vector_store import SearchResult, similarity_search

logger = logging.getLogger("udyamsetu.rag")


# ---------------------------------------------------------------------------
# RAG context builder
# ---------------------------------------------------------------------------

@dataclass
class RAGContext:
    """Assembled context for a RAG-augmented generation call."""
    retrieved_chunks: List[SearchResult] = field(default_factory=list)
    platform_context: Dict[str, Any] = field(default_factory=dict)
    augmented_prompt: str = ""
    total_context_tokens: int = 0


def build_context_prompt(
    chunks: List[SearchResult],
    platform_context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build a context-augmented system prompt from retrieved chunks
    and optional platform context (business profile, compliance status, etc.).
    """
    sections = []

    # Platform context section
    if platform_context:
        ctx_parts = ["=== USER'S BUSINESS CONTEXT ==="]
        if "business_name" in platform_context:
            ctx_parts.append(f"Business: {platform_context['business_name']}")
        if "industry_type" in platform_context:
            ctx_parts.append(f"Industry: {platform_context['industry_type']}")
        if "msme_category" in platform_context:
            ctx_parts.append(f"MSME Category: {platform_context['msme_category']}")
        if "state" in platform_context:
            ctx_parts.append(f"State: {platform_context['state']}")
        if "investment" in platform_context:
            ctx_parts.append(f"Investment: ₹{platform_context['investment']}")
        if "employee_count" in platform_context:
            ctx_parts.append(f"Employees: {platform_context['employee_count']}")
        if "compliance_score" in platform_context:
            ctx_parts.append(f"Compliance Score: {platform_context['compliance_score']}%")
        if "pending_approvals" in platform_context:
            ctx_parts.append(f"Pending Approvals: {', '.join(platform_context['pending_approvals'])}")
        sections.append("\n".join(ctx_parts))

    # Retrieved knowledge context
    if chunks:
        kb_parts = ["=== RELEVANT KNOWLEDGE BASE CONTEXT ==="]
        kb_parts.append(
            "Use the following verified information to ground your response. "
            "Cite source documents by [Source N] notation when referencing this context."
        )
        for i, chunk in enumerate(chunks, 1):
            kb_parts.append(
                f"\n[Source {i}] {chunk.document_title} "
                f"(Category: {chunk.category}, Relevance: {chunk.similarity_score:.0%})\n"
                f"{chunk.content}"
            )
        sections.append("\n".join(kb_parts))

    if not sections:
        return ""

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Core RAG pipeline
# ---------------------------------------------------------------------------

async def rag_generate(
    db: AsyncSession,
    user_message: str,
    *,
    conversation_history: Optional[List[ChatMessage]] = None,
    platform_context: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    min_score: float = 0.25,
    category_filter: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> tuple[AIResponse, RAGContext]:
    """
    Execute the full RAG pipeline:
    1. Embed user query
    2. Retrieve relevant knowledge chunks
    3. Build augmented system prompt
    4. Generate grounded response with citations
    """
    provider = get_ai_provider()
    rag_context = RAGContext()

    # Step 1: Embed the user query
    try:
        embedding_result = await provider.embed([user_message])
        query_embedding = embedding_result.embeddings[0]
    except Exception as e:
        logger.warning(f"Embedding failed, proceeding without RAG: {e}")
        query_embedding = None

    # Step 2: Retrieve relevant chunks
    if query_embedding:
        try:
            chunks = await similarity_search(
                db,
                query_embedding,
                top_k=top_k,
                min_score=min_score,
                category_filter=category_filter,
            )
            rag_context.retrieved_chunks = chunks
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")

    # Step 3: Build augmented system prompt
    context_prompt = build_context_prompt(
        rag_context.retrieved_chunks,
        platform_context,
    )
    full_system_prompt = UDYAMSETU_SYSTEM_PROMPT
    if context_prompt:
        full_system_prompt += f"\n\n{context_prompt}"
    rag_context.augmented_prompt = full_system_prompt

    # Step 4: Build message history
    messages = conversation_history or []
    messages.append(ChatMessage(role=MessageRole.USER, content=user_message))

    # Step 5: Generate response
    response = await provider.generate(
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
        system_prompt=full_system_prompt,
    )

    # Step 6: Attach source citations to response
    if rag_context.retrieved_chunks:
        response.sources = [
            {
                "index": i + 1,
                "document_id": chunk.document_id,
                "document_title": chunk.document_title,
                "category": chunk.category,
                "relevance_score": round(chunk.similarity_score, 4),
                "chunk_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
            }
            for i, chunk in enumerate(rag_context.retrieved_chunks)
        ]

    return response, rag_context


# ---------------------------------------------------------------------------
# Conversation management helpers
# ---------------------------------------------------------------------------

async def create_conversation(
    db: AsyncSession,
    user_id: str,
    *,
    title: str = "New Conversation",
    business_id: Optional[str] = None,
    context_type: Optional[str] = None,
) -> Conversation:
    """Create a new AI conversation."""
    conversation = Conversation(
        user_id=user_id,
        title=title,
        business_id=business_id,
        context_type=context_type or "general",
    )
    db.add(conversation)
    await db.flush()
    return conversation


async def add_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    *,
    model_used: Optional[str] = None,
    provider_used: Optional[str] = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    sources: Optional[List[Dict[str, Any]]] = None,
    confidence_score: Optional[float] = None,
) -> ConversationMessage:
    """Add a message to a conversation and update counters."""
    # Get current message count for sequence numbering
    result = await db.execute(
        select(func.count(ConversationMessage.id)).where(
            ConversationMessage.conversation_id == conversation_id
        )
    )
    seq_num = (result.scalar() or 0) + 1

    message = ConversationMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sequence_number=seq_num,
        model_used=model_used,
        provider_used=provider_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        sources=sources,
        confidence_score=confidence_score,
    )
    db.add(message)

    # Update conversation counters
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    if conversation:
        conversation.total_messages = seq_num
        conversation.total_tokens_used += total_tokens
        from app.models.base import utc_now
        conversation.last_message_at = utc_now()

        # Auto-generate title from first user message
        if seq_num <= 2 and role == "user" and conversation.title == "New Conversation":
            title_text = content[:80].strip()
            if len(content) > 80:
                title_text += "..."
            conversation.title = title_text

    await db.flush()
    return message


async def get_conversation_history(
    db: AsyncSession,
    conversation_id: str,
    *,
    limit: int = 50,
) -> List[ChatMessage]:
    """Load conversation message history as ChatMessage objects for the AI."""
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.sequence_number)
        .limit(limit)
    )
    messages = result.scalars().all()

    return [
        ChatMessage(
            role=MessageRole(msg.role),
            content=msg.content,
        )
        for msg in messages
        if msg.role in ("user", "assistant")
    ]


async def get_user_conversations(
    db: AsyncSession,
    user_id: str,
    *,
    status: str = "active",
    limit: int = 50,
    offset: int = 0,
) -> List[Conversation]:
    """List a user's conversations with pagination."""
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.status == status,
        )
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_ai_next_actions(
    db: AsyncSession,
    user_id: str,
    business_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    AI-powered next-action suggestions based on the user's current
    platform state (compliance gaps, pending approvals, scheme eligibility).
    """
    provider = get_ai_provider()

    # Build a concise platform state summary
    platform_summary = []
    platform_summary.append("Generate 3-5 prioritized next actions for this MSME user based on their platform state.")

    if business_id:
        # Could query actual business data here; for now give a structured prompt
        platform_summary.append(
            "Consider: pending approvals, upcoming compliance deadlines, "
            "eligible government schemes, and document gaps."
        )

    prompt = "\n".join(platform_summary)

    messages = [ChatMessage(role=MessageRole.USER, content=prompt)]

    response = await provider.generate(
        messages,
        temperature=0.5,
        max_tokens=1024,
        system_prompt=(
            UDYAMSETU_SYSTEM_PROMPT +
            "\n\nRespond with a JSON array of action objects, each with: "
            "'priority' (1-5), 'action' (short title), 'description' (1-2 sentences), "
            "'category' (approvals/compliance/schemes/documents), 'urgency' (high/medium/low)."
        ),
    )

    return {
        "suggestions": response.content,
        "model": response.model,
        "provider": response.provider,
    }
