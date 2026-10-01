"""
End-to-end integration test suite for Document Intelligence Pipeline (Fragment 75).
Covers:
  - Document Health API (/documents/business/{business_id}/health)
  - Document Processing trigger API (/documents/{document_id}/process)
  - Role-based authorization & security isolation
  - End-to-end flow: Document registration -> AI processing -> Health score recalculation
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import create_access_token
from app.main import app
from app.models.business import Business, EntityType, MSMECategory
from app.models.document import Document, DocumentType, DocumentVerificationStatus
from app.models.user import User, UserRole
from app.services.storage_service import StorageService


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def e2e_fixtures():
    """Create test users, businesses, and sample documents."""
    async with AsyncSessionLocal() as session:
        owner = User(
            email="owner@ecosteel.in",
            hashed_password="SecurePassword123!",
            full_name="Rajesh Sharma",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        intruder = User(
            email="rival@competitor.in",
            hashed_password="SecurePassword123!",
            full_name="Rival User",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        officer = User(
            email="officer@env.gov.in",
            hashed_password="SecurePassword123!",
            full_name="Officer Rao",
            role=UserRole.DEPARTMENT_OFFICER,
            department_id="ENV",
            is_active=True,
            is_verified=True,
        )
        session.add_all([owner, intruder, officer])
        await session.commit()
        await session.refresh(owner)
        await session.refresh(intruder)
        await session.refresh(officer)

        biz = Business(
            user_id=owner.id,
            legal_name="EcoSteel Industries Pvt Ltd",
            entity_type=EntityType.PRIVATE_LIMITED,
            msme_category=MSMECategory.MEDIUM,
            pan="ABCDE1234F",
            is_active=True,
        )
        session.add(biz)
        await session.commit()
        await session.refresh(biz)

        # Upload a dummy file to storage service (must be > 5KB to pass completeness check)
        storage = StorageService()
        dummy_content = b"%PDF-1.4\n" + b"PAN CARD SCAN DATA " * 350 + b"\n%%EOF"
        file_path, file_hash, file_size = storage.store(
            business_id=str(biz.id),
            filename="pan_card.pdf",
            mime_type="application/pdf",
            data=dummy_content,
        )

        doc = Document(
            business_id=biz.id,
            uploaded_by_user_id=owner.id,
            file_name="pan_card.pdf",
            storage_path=file_path,
            file_size_bytes=file_size,
            sha256_checksum=file_hash,
            mime_type="application/pdf",
            document_type=DocumentType.PAN_CARD,
            verification_status=DocumentVerificationStatus.PENDING,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        return {
            "owner": owner,
            "intruder": intruder,
            "officer": officer,
            "business": biz,
            "document": doc,
            "storage_path": file_path,
            "storage": storage,
        }


def make_auth_headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Document Health Tests (Fragment 73)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_document_health_owner_success(e2e_fixtures):
    """Test owner can fetch document health dashboard."""
    owner = e2e_fixtures["owner"]
    biz = e2e_fixtures["business"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/documents/business/{biz.id}/health",
            headers=make_auth_headers(owner),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["business_id"] == str(biz.id)
    assert "completeness_score" in data
    assert "health_grade" in data
    assert data["total_documents"] == 1
    assert data["pending_count"] == 1
    assert data["verified_count"] == 0


@pytest.mark.asyncio
async def test_get_document_health_officer_access(e2e_fixtures):
    """Test officer can view any business document health."""
    officer = e2e_fixtures["officer"]
    biz = e2e_fixtures["business"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/documents/business/{biz.id}/health",
            headers=make_auth_headers(officer),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["business_id"] == str(biz.id)


@pytest.mark.asyncio
async def test_get_document_health_intruder_forbidden(e2e_fixtures):
    """Test competing business cannot access another business health report."""
    intruder = e2e_fixtures["intruder"]
    biz = e2e_fixtures["business"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/documents/business/{biz.id}/health",
            headers=make_auth_headers(intruder),
        )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Document Processing Trigger Tests (Fragment 74)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_document_success(e2e_fixtures):
    """Test owner triggers processing and pipeline extracts entities & verifies."""
    owner = e2e_fixtures["owner"]
    doc = e2e_fixtures["document"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/documents/{doc.id}/process",
            headers=make_auth_headers(owner),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == str(doc.id)
    assert data["success"] is True
    assert data["detected_type"] == "PAN_CARD"
    assert data["confidence"] is not None
    assert data["confidence"] > 0


@pytest.mark.asyncio
async def test_process_document_intruder_forbidden(e2e_fixtures):
    """Test non-owner cannot trigger processing on another business document."""
    intruder = e2e_fixtures["intruder"]
    doc = e2e_fixtures["document"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/documents/{doc.id}/process",
            headers=make_auth_headers(intruder),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_process_document_not_found(e2e_fixtures):
    """Test 404 for non-existent document ID."""
    owner = e2e_fixtures["owner"]
    import uuid

    fake_id = uuid.uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/documents/{fake_id}/process",
            headers=make_auth_headers(owner),
        )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# End-to-End Flow (Fragment 75)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_document_pipeline_e2e_flow(e2e_fixtures):
    """
    Complete E2E workflow:
    1. Query health dashboard: document is PENDING, score is 0.
    2. Trigger processing: OCR runs, extracts fields, verifies document.
    3. Query health dashboard again: status is VERIFIED, completeness score updated.
    """
    owner = e2e_fixtures["owner"]
    biz = e2e_fixtures["business"]
    doc = e2e_fixtures["document"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Step 1: Initial health
        h1 = await ac.get(
            f"/api/v1/documents/business/{biz.id}/health",
            headers=make_auth_headers(owner),
        )
        assert h1.status_code == 200
        assert h1.json()["pending_count"] == 1
        assert h1.json()["verified_count"] == 0

        # Step 2: Trigger processing
        proc = await ac.post(
            f"/api/v1/documents/{doc.id}/process",
            headers=make_auth_headers(owner),
        )
        assert proc.status_code == 200
        proc_data = proc.json()
        assert proc_data["verification_status"] == "VERIFIED"

        # Step 3: Verify updated health
        h2 = await ac.get(
            f"/api/v1/documents/business/{biz.id}/health",
            headers=make_auth_headers(owner),
        )
        assert h2.status_code == 200
        h2_data = h2.json()
        assert h2_data["verified_count"] == 1
        assert h2_data["pending_count"] == 0
