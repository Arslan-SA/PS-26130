"""
Chat API — UdyamSetu AI Assistant

REST endpoints for AI-powered chat conversations with RAG-grounded
responses, conversation management, knowledge base operations,
and AI next-action suggestions.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_admin
from app.models.conversation import Conversation, ConversationMessage, ConversationStatus
from app.models.knowledge_document import KnowledgeDocument, ProcessingStatus
from app.models.user import User
from app.services.rag_service import (
    rag_generate,
    create_conversation,
    add_message,
    get_conversation_history,
    get_user_conversations,
    get_ai_next_actions,
)
from app.services.embedding_service import (
    seed_knowledge_base,
    process_document_embeddings,
)
from app.services.vector_store import get_knowledge_stats

logger = logging.getLogger("udyamsetu.chat_api")

router = APIRouter(prefix="/chat", tags=["AI Assistant"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CreateConversationRequest(BaseModel):
    title: str = Field(default="New Conversation", max_length=255)
    context_type: Optional[str] = Field(default="general", max_length=50)
    business_id: Optional[str] = None


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    context_type: Optional[str] = None


class RateMessageRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)


class AddKnowledgeDocumentRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=10)
    category: str = Field(default="regulatory", max_length=30)
    source_url: Optional[str] = None
    metadata: Optional[dict] = None


# ---------------------------------------------------------------------------
# Conversation endpoints
# ---------------------------------------------------------------------------

@router.post("/conversations")
async def api_create_conversation(
    request: CreateConversationRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new AI chat conversation."""
    conversation = await create_conversation(
        db,
        user_id=user.id,
        title=request.title,
        business_id=request.business_id,
        context_type=request.context_type,
    )
    return {
        "status": "success",
        "conversation": conversation.to_summary_dict(),
    }


@router.get("/conversations")
async def api_list_conversations(
    status: str = Query(default="active"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's conversations."""
    conversations = await get_user_conversations(
        db,
        user_id=user.id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {
        "status": "success",
        "conversations": [c.to_summary_dict() for c in conversations],
        "total": len(conversations),
    }


@router.get("/conversations/{conversation_id}")
async def api_get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a conversation with its full message history."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "status": "success",
        "conversation": conversation.to_dict(),
    }


@router.delete("/conversations/{conversation_id}")
async def api_delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive (soft-delete) a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.status = ConversationStatus.ARCHIVED.value
    await db.flush()

    return {"status": "success", "message": "Conversation archived"}


# ---------------------------------------------------------------------------
# Message / chat endpoints
# ---------------------------------------------------------------------------

@router.post("/conversations/{conversation_id}/messages")
async def api_send_message(
    conversation_id: str,
    request: SendMessageRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message in a conversation and receive an AI response.
    Uses RAG to ground responses in the knowledge base.
    """
    # Verify conversation ownership
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.status != ConversationStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Conversation is not active")

    # Save user message
    user_msg = await add_message(
        db,
        conversation_id=conversation_id,
        role="user",
        content=request.message,
    )

    # Build platform context from user's business
    platform_context = None
    if conversation.business_id:
        from app.models.business import Business
        biz_result = await db.execute(
            select(Business).where(Business.id == conversation.business_id)
        )
        business = biz_result.scalar_one_or_none()
        if business:
            platform_context = {
                "business_name": business.name,
                "industry_type": getattr(business, "industry_type", None),
                "msme_category": getattr(business, "msme_category", None),
                "state": getattr(business, "state", None),
            }

    # Load conversation history
    history = await get_conversation_history(db, conversation_id, limit=20)

    # Execute RAG pipeline
    category_filter = request.context_type or conversation.context_type
    if category_filter == "general":
        category_filter = None

    ai_response, rag_context = await rag_generate(
        db,
        request.message,
        conversation_history=history[:-1],  # Exclude the message we just added
        platform_context=platform_context,
        category_filter=category_filter,
    )

    # Save assistant response
    assistant_msg = await add_message(
        db,
        conversation_id=conversation_id,
        role="assistant",
        content=ai_response.content,
        model_used=ai_response.model,
        provider_used=ai_response.provider,
        prompt_tokens=ai_response.usage.get("prompt_tokens", 0),
        completion_tokens=ai_response.usage.get("completion_tokens", 0),
        total_tokens=ai_response.usage.get("total_tokens", 0),
        sources=ai_response.sources if ai_response.sources else None,
        confidence_score=max(
            (c.similarity_score for c in rag_context.retrieved_chunks), default=None
        ) if rag_context.retrieved_chunks else None,
    )

    return {
        "status": "success",
        "user_message": user_msg.to_dict(),
        "assistant_message": assistant_msg.to_dict(),
        "sources": ai_response.sources,
        "model": ai_response.model,
        "provider": ai_response.provider,
        "usage": ai_response.usage,
    }


@router.post("/quick")
async def api_quick_chat(
    request: SendMessageRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Quick one-shot chat without creating a persistent conversation.
    Useful for single questions and inline help.
    """
    ai_response, rag_context = await rag_generate(
        db,
        request.message,
        category_filter=request.context_type if request.context_type != "general" else None,
    )

    return {
        "status": "success",
        "response": ai_response.content,
        "sources": ai_response.sources,
        "model": ai_response.model,
        "provider": ai_response.provider,
        "usage": ai_response.usage,
    }


@router.post("/messages/{message_id}/rate")
async def api_rate_message(
    message_id: str,
    request: RateMessageRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Rate an AI response (thumbs up/down)."""
    result = await db.execute(
        select(ConversationMessage)
        .join(Conversation)
        .where(
            ConversationMessage.id == message_id,
            Conversation.user_id == user.id,
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    message.user_rating = request.rating
    await db.flush()

    return {"status": "success", "message": "Rating saved"}


# ---------------------------------------------------------------------------
# AI next-action suggestions
# ---------------------------------------------------------------------------

@router.get("/next-actions")
async def api_get_next_actions(
    business_id: Optional[str] = None,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-powered next-action suggestions for the user."""
    suggestions = await get_ai_next_actions(
        db,
        user_id=user.id,
        business_id=business_id,
    )
    return {"status": "success", **suggestions}


# ---------------------------------------------------------------------------
# Knowledge base management (admin-only)
# ---------------------------------------------------------------------------

@router.post("/knowledge/seed")
async def api_seed_knowledge_base(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Seed the knowledge base with core regulatory documents (admin only)."""
    docs = await seed_knowledge_base(db)
    return {
        "status": "success",
        "message": f"Seeded {len(docs)} knowledge documents",
        "documents": [d.to_dict() for d in docs],
    }


@router.post("/knowledge/documents")
async def api_add_knowledge_document(
    request: AddKnowledgeDocumentRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Add a new document to the knowledge base and process its embeddings."""
    doc = KnowledgeDocument(
        title=request.title,
        content=request.content,
        category=request.category,
        source_url=request.source_url,
        metadata_json=request.metadata,
        processing_status=ProcessingStatus.PENDING.value,
    )
    db.add(doc)
    await db.flush()

    # Process embeddings
    await process_document_embeddings(db, doc.id)

    return {
        "status": "success",
        "document": doc.to_dict(),
    }


@router.get("/knowledge/documents")
async def api_list_knowledge_documents(
    category: Optional[str] = None,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all knowledge base documents."""
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.is_active == True)
    if category:
        stmt = stmt.where(KnowledgeDocument.category == category)
    stmt = stmt.order_by(KnowledgeDocument.created_at.desc())

    result = await db.execute(stmt)
    docs = result.scalars().all()

    return {
        "status": "success",
        "documents": [d.to_dict() for d in docs],
        "total": len(docs),
    }


@router.get("/knowledge/stats")
async def api_knowledge_stats(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge base statistics."""
    stats = await get_knowledge_stats(db)
    return {"status": "success", **stats}
