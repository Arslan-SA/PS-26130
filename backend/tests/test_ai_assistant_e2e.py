"""
AI Assistant End-to-End Test Suite — UdyamSetu AI (Phase 9)

Tests the full AI/RAG pipeline: provider abstraction, conversation management,
knowledge base operations, embedding pipeline, vector similarity search,
RAG-grounded response generation, source citations, and next-action integration.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import engine, Base, AsyncSessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Provide a clean async session."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def industry_user(db_session) -> dict:
    """Create an industry user and return auth headers."""
    user = User(
        email="ai_test_user@example.com",
        full_name="AI Test User",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.INDUSTRY_USER,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token({"sub": user.id, "role": user.role.value})
    return {"user": user, "headers": {"Authorization": f"Bearer {token}"}}


@pytest_asyncio.fixture
async def admin_user(db_session) -> dict:
    """Create an admin user and return auth headers."""
    user = User(
        email="ai_admin@example.com",
        full_name="AI Admin User",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token({"sub": user.id, "role": user.role.value})
    return {"user": user, "headers": {"Authorization": f"Bearer {token}"}}


@pytest_asyncio.fixture
async def client():
    """Provide an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# AI Service Abstraction Tests
# ---------------------------------------------------------------------------

class TestAIServiceAbstraction:
    """Fragment 113–114: AI provider factory and mock provider."""

    @pytest.mark.asyncio
    async def test_mock_provider_generate(self):
        """Mock provider should return deterministic responses."""
        from app.services.ai_service import MockProvider, ChatMessage, MessageRole

        provider = MockProvider()
        messages = [ChatMessage(role=MessageRole.USER, content="Tell me about udyam registration")]
        response = await provider.generate(messages)

        assert response.provider == "mock"
        assert response.model == "mock-v1"
        assert "Udyam" in response.content
        assert response.usage["total_tokens"] > 0

    @pytest.mark.asyncio
    async def test_mock_provider_embed(self):
        """Mock provider should return deterministic embeddings."""
        from app.services.ai_service import MockProvider

        provider = MockProvider()
        result = await provider.embed(["test text", "another text"])

        assert result.provider == "mock"
        assert len(result.embeddings) == 2
        assert result.dimensions == 256
        assert all(len(e) == 256 for e in result.embeddings)

    @pytest.mark.asyncio
    async def test_mock_embeddings_deterministic(self):
        """Same text should produce identical embeddings."""
        from app.services.ai_service import MockProvider

        provider = MockProvider()
        r1 = await provider.embed(["hello world"])
        r2 = await provider.embed(["hello world"])

        assert r1.embeddings[0] == r2.embeddings[0]

    @pytest.mark.asyncio
    async def test_provider_factory_default_mock(self):
        """Default provider should be mock."""
        from app.services.ai_service import get_ai_provider, reset_ai_provider

        reset_ai_provider()
        provider = get_ai_provider()
        assert provider.provider_name() == "mock"
        reset_ai_provider()

    @pytest.mark.asyncio
    async def test_mock_knowledge_matching(self):
        """Mock provider should match queries to domain knowledge."""
        from app.services.ai_service import MockProvider, ChatMessage, MessageRole

        provider = MockProvider()

        # GST-related query
        messages = [ChatMessage(role=MessageRole.USER, content="How to register for GST?")]
        response = await provider.generate(messages)
        assert "GST" in response.content

        # Scheme-related query
        messages = [ChatMessage(role=MessageRole.USER, content="What is the PMEGP scheme?")]
        response = await provider.generate(messages)
        assert "scheme" in response.content.lower() or "MSME" in response.content


# ---------------------------------------------------------------------------
# Conversation Model Tests
# ---------------------------------------------------------------------------

class TestConversationModel:
    """Fragment 115: Conversation and message models."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, db_session, industry_user):
        """Should create a conversation with proper defaults."""
        from app.models.conversation import Conversation

        conv = Conversation(
            user_id=industry_user["user"].id,
            title="Test Conversation",
            context_type="approvals",
        )
        db_session.add(conv)
        await db_session.flush()

        assert conv.id is not None
        assert conv.status == "active"
        assert conv.total_messages == 0

    @pytest.mark.asyncio
    async def test_create_message(self, db_session, industry_user):
        """Should create messages with proper sequence numbering."""
        from app.models.conversation import Conversation, ConversationMessage

        conv = Conversation(
            user_id=industry_user["user"].id,
            title="Test Conv",
        )
        db_session.add(conv)
        await db_session.flush()

        msg = ConversationMessage(
            conversation_id=conv.id,
            role="user",
            content="Hello AI",
            sequence_number=1,
        )
        db_session.add(msg)
        await db_session.flush()

        assert msg.id is not None
        assert msg.role == "user"
        assert msg.sequence_number == 1


# ---------------------------------------------------------------------------
# Knowledge Document Model Tests
# ---------------------------------------------------------------------------

class TestKnowledgeDocumentModel:
    """Fragment 118: Knowledge document and chunk models."""

    @pytest.mark.asyncio
    async def test_create_knowledge_document(self, db_session):
        """Should create a knowledge document with proper defaults."""
        from app.models.knowledge_document import KnowledgeDocument

        doc = KnowledgeDocument(
            title="Test Document",
            content="This is test content for the knowledge base.",
            category="regulatory",
        )
        db_session.add(doc)
        await db_session.flush()

        assert doc.id is not None
        assert doc.processing_status == "pending"
        assert doc.chunk_count == 0

    @pytest.mark.asyncio
    async def test_create_knowledge_chunk(self, db_session):
        """Should create a knowledge chunk with embedding data."""
        from app.models.knowledge_document import KnowledgeDocument, KnowledgeChunk

        doc = KnowledgeDocument(
            title="Test Doc",
            content="Test content",
            category="regulatory",
        )
        db_session.add(doc)
        await db_session.flush()

        chunk = KnowledgeChunk(
            document_id=doc.id,
            chunk_index=0,
            content="First chunk of content",
            token_count=4,
            embedding=[0.1, 0.2, 0.3],
            embedding_model="mock-v1",
            embedding_dimensions=3,
        )
        db_session.add(chunk)
        await db_session.flush()

        assert chunk.id is not None
        assert chunk.embedding == [0.1, 0.2, 0.3]


# ---------------------------------------------------------------------------
# Embedding Pipeline Tests
# ---------------------------------------------------------------------------

class TestEmbeddingPipeline:
    """Fragment 119: Text chunking and embedding generation."""

    def test_chunk_text_basic(self):
        """Should split text into chunks."""
        from app.services.embedding_service import chunk_text

        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = chunk_text(text, max_tokens=20)
        assert len(chunks) >= 1
        assert all(len(c) > 0 for c in chunks)

    def test_chunk_text_empty(self):
        """Should handle empty text."""
        from app.services.embedding_service import chunk_text

        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_chunk_text_single_paragraph(self):
        """Should return single chunk for short text."""
        from app.services.embedding_service import chunk_text

        chunks = chunk_text("Short text here.", max_tokens=100)
        assert len(chunks) == 1
        assert chunks[0] == "Short text here."

    @pytest.mark.asyncio
    async def test_process_document_embeddings(self, db_session):
        """Should process a document through the embedding pipeline."""
        from app.models.knowledge_document import KnowledgeDocument
        from app.services.embedding_service import process_document_embeddings

        doc = KnowledgeDocument(
            title="Embedding Test",
            content="First section about Udyam registration.\n\nSecond section about GST compliance.",
            category="regulatory",
        )
        db_session.add(doc)
        await db_session.flush()

        result = await process_document_embeddings(db_session, doc.id)
        assert result.processing_status == "completed"
        assert result.chunk_count > 0


# ---------------------------------------------------------------------------
# Vector Store Tests
# ---------------------------------------------------------------------------

class TestVectorStore:
    """Fragment 120: Similarity search over embeddings."""

    @pytest.mark.asyncio
    async def test_cosine_similarity(self):
        """Should compute cosine similarity correctly."""
        from app.services.vector_store import cosine_similarity

        # Identical vectors → 1.0
        assert abs(cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 0.01
        # Orthogonal vectors → 0.0
        assert abs(cosine_similarity([1, 0, 0], [0, 1, 0])) < 0.01
        # Opposite vectors → -1.0
        assert abs(cosine_similarity([1, 0, 0], [-1, 0, 0]) - (-1.0)) < 0.01

    @pytest.mark.asyncio
    async def test_similarity_search(self, db_session):
        """Should find similar chunks via embedding similarity."""
        from app.models.knowledge_document import KnowledgeDocument
        from app.services.embedding_service import process_document_embeddings
        from app.services.vector_store import similarity_search
        from app.services.ai_service import MockProvider

        # Create and process a document
        doc = KnowledgeDocument(
            title="Search Test Doc",
            content="Information about industrial factory licenses and regulations.",
            category="regulatory",
        )
        db_session.add(doc)
        await db_session.flush()
        await process_document_embeddings(db_session, doc.id)

        # Embed query and search
        provider = MockProvider()
        query_embedding = (await provider.embed(["factory license"])).embeddings[0]
        results = await similarity_search(db_session, query_embedding, min_score=0.0)

        assert len(results) > 0
        assert results[0].document_title == "Search Test Doc"


# ---------------------------------------------------------------------------
# RAG Pipeline Tests
# ---------------------------------------------------------------------------

class TestRAGPipeline:
    """Fragments 121–123: RAG retrieval, grounded generation, source references."""

    @pytest.mark.asyncio
    async def test_rag_generate(self, db_session):
        """Should generate a RAG-grounded response with sources."""
        from app.models.knowledge_document import KnowledgeDocument
        from app.services.embedding_service import process_document_embeddings
        from app.services.rag_service import rag_generate

        # Seed knowledge
        doc = KnowledgeDocument(
            title="RAG Test Document",
            content="Udyam Registration is mandatory for all MSMEs in India.",
            category="regulatory",
        )
        db_session.add(doc)
        await db_session.flush()
        await process_document_embeddings(db_session, doc.id)

        # Generate response
        response, context = await rag_generate(
            db_session,
            "Tell me about Udyam Registration",
            min_score=0.0,
        )

        assert response.content
        assert response.provider == "mock"

    @pytest.mark.asyncio
    async def test_conversation_management(self, db_session, industry_user):
        """Should create conversations and manage message history."""
        from app.services.rag_service import (
            create_conversation,
            add_message,
            get_conversation_history,
        )

        conv = await create_conversation(
            db_session, user_id=industry_user["user"].id, title="Test"
        )
        assert conv.id is not None

        await add_message(db_session, conv.id, "user", "Hello")
        await add_message(db_session, conv.id, "assistant", "Hi there!")

        history = await get_conversation_history(db_session, conv.id)
        assert len(history) == 2
        assert history[0].role.value == "user"
        assert history[1].role.value == "assistant"


# ---------------------------------------------------------------------------
# Chat API Tests
# ---------------------------------------------------------------------------

class TestChatAPI:
    """Fragment 116: Chat REST API endpoints."""

    @pytest.mark.asyncio
    async def test_create_conversation_api(self, client, industry_user):
        """POST /chat/conversations should create a conversation."""
        res = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "API Test Conversation"},
            headers=industry_user["headers"],
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["conversation"]["title"] == "API Test Conversation"

    @pytest.mark.asyncio
    async def test_list_conversations_api(self, client, industry_user):
        """GET /chat/conversations should list user conversations."""
        # Create one first
        await client.post(
            "/api/v1/chat/conversations",
            json={"title": "List Test"},
            headers=industry_user["headers"],
        )

        res = await client.get(
            "/api/v1/chat/conversations",
            headers=industry_user["headers"],
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert len(data["conversations"]) >= 1

    @pytest.mark.asyncio
    async def test_send_message_api(self, client, industry_user):
        """POST /chat/conversations/{id}/messages should return AI response."""
        # Create conversation
        create_res = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Message Test"},
            headers=industry_user["headers"],
        )
        conv_id = create_res.json()["conversation"]["id"]

        # Send message
        res = await client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages",
            json={"message": "What is Udyam registration?"},
            headers=industry_user["headers"],
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["user_message"]["role"] == "user"
        assert data["assistant_message"]["role"] == "assistant"
        assert len(data["assistant_message"]["content"]) > 0

    @pytest.mark.asyncio
    async def test_quick_chat_api(self, client, industry_user):
        """POST /chat/quick should return a quick response without conversation."""
        res = await client.post(
            "/api/v1/chat/quick",
            json={"message": "What is GST?"},
            headers=industry_user["headers"],
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert len(data["response"]) > 0

    @pytest.mark.asyncio
    async def test_delete_conversation_api(self, client, industry_user):
        """DELETE /chat/conversations/{id} should archive the conversation."""
        create_res = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Delete Test"},
            headers=industry_user["headers"],
        )
        conv_id = create_res.json()["conversation"]["id"]

        res = await client.delete(
            f"/api/v1/chat/conversations/{conv_id}",
            headers=industry_user["headers"],
        )
        assert res.status_code == 200
        assert res.json()["status"] == "success"

    @pytest.mark.asyncio
    async def test_get_conversation_detail(self, client, industry_user):
        """GET /chat/conversations/{id} should include message history."""
        # Create and send message
        create_res = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Detail Test"},
            headers=industry_user["headers"],
        )
        conv_id = create_res.json()["conversation"]["id"]

        await client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages",
            json={"message": "Test question"},
            headers=industry_user["headers"],
        )

        # Get detail
        res = await client.get(
            f"/api/v1/chat/conversations/{conv_id}",
            headers=industry_user["headers"],
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["conversation"]["messages"]) >= 2


# ---------------------------------------------------------------------------
# Knowledge Base API Tests
# ---------------------------------------------------------------------------

class TestKnowledgeBaseAPI:
    """Fragment 118-119: Knowledge base management."""

    @pytest.mark.asyncio
    async def test_seed_knowledge_base(self, client, admin_user):
        """POST /chat/knowledge/seed should seed documents (admin only)."""
        res = await client.post(
            "/api/v1/chat/knowledge/seed",
            headers=admin_user["headers"],
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert len(data["documents"]) > 0

    @pytest.mark.asyncio
    async def test_list_knowledge_documents(self, client, industry_user, admin_user):
        """GET /chat/knowledge/documents should list knowledge docs."""
        # Seed first
        await client.post("/api/v1/chat/knowledge/seed", headers=admin_user["headers"])

        res = await client.get(
            "/api/v1/chat/knowledge/documents",
            headers=industry_user["headers"],
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] > 0

    @pytest.mark.asyncio
    async def test_knowledge_stats(self, client, industry_user):
        """GET /chat/knowledge/stats should return stats."""
        res = await client.get(
            "/api/v1/chat/knowledge/stats",
            headers=industry_user["headers"],
        )
        assert res.status_code == 200
        data = res.json()
        assert "total_documents" in data

    @pytest.mark.asyncio
    async def test_add_knowledge_document(self, client, admin_user):
        """POST /chat/knowledge/documents should add and process a doc."""
        res = await client.post(
            "/api/v1/chat/knowledge/documents",
            json={
                "title": "Custom Knowledge Doc",
                "content": "This is custom knowledge content for testing purposes. It should be chunked and embedded.",
                "category": "regulatory",
            },
            headers=admin_user["headers"],
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["document"]["processing_status"] == "completed"


# ---------------------------------------------------------------------------
# AI Next-Action Tests
# ---------------------------------------------------------------------------

class TestAINextActions:
    """Fragment 124: AI-powered next-action suggestions."""

    @pytest.mark.asyncio
    async def test_next_actions_api(self, client, industry_user):
        """GET /chat/next-actions should return suggestions."""
        res = await client.get(
            "/api/v1/chat/next-actions",
            headers=industry_user["headers"],
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "suggestions" in data
