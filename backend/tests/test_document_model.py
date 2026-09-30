"""
Unit tests for Document domain model (Fragment 59).
Tests model instantiation, relationships, enums, JSON metadata, and database persistence.
"""

from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal, Base, engine
from app.models.approval import Approval
from app.models.approval_requirement import ApprovalRequirement, RequirementStage, RequirementStatus
from app.models.business import Business, EntityType, MSMECategory
from app.models.document import Document, DocumentType, DocumentVerificationStatus
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_document_model_creation_and_relationships():
    """Verify document creation, default values, and relationships with business and requirement."""
    async with AsyncSessionLocal() as session:
        # Create user
        user = User(
            email="promoter@zenithpharma.in",
            hashed_password="SecurePassword123!",
            full_name="Dr. Shashi Zenith",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Create business
        biz = Business(
            user_id=user.id,
            legal_name="Zenith Active Pharma Ingredients Ltd",
            trade_name="Zenith Pharma",
            entity_type=EntityType.PUBLIC_LIMITED,
            msme_category=MSMECategory.MEDIUM,
            pan="AAACZ9999M",
            gstin="27AAACZ9999M1Z1",
        )
        session.add(biz)
        await session.commit()
        await session.refresh(biz)

        # Create approval and requirement
        app = Approval(
            code="CTE_PCB",
            title="Consent to Establish (CTE)",
            department_code="SPCB",
            issuing_authority="State Pollution Control Board",
            is_mandatory=True,
            sla_days=45,
            estimated_fee_base=25000.0,
        )
        session.add(app)
        await session.commit()
        await session.refresh(app)

        req = ApprovalRequirement(
            business_id=biz.id,
            approval_id=app.id,
            stage=RequirementStage.PRE_ESTABLISHMENT,
            status=RequirementStatus.IN_PROGRESS,
            is_mandatory=True,
            trigger_reason="Pharma API manufacturing produces industrial effluents",
            estimated_fee=35000.0,
            sla_deadline_days=45,
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)

        # Create document
        doc = Document(
            business_id=biz.id,
            uploaded_by_user_id=user.id,
            requirement_id=req.id,
            document_type=DocumentType.ENVIRONMENTAL_MANAGEMENT_PLAN,
            file_name="EMP_Zenith_Pharma_v1.pdf",
            storage_path="documents/biz-123/emp_zenith_pharma_v1.pdf",
            mime_type="application/pdf",
            file_size_bytes=2048500,
            sha256_checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            verification_status=DocumentVerificationStatus.VERIFIED,
            ocr_raw_text="Effluent Treatment Plant Design Capacity: 100 KLD. ZLD System Installed.",
            extracted_metadata={
                "etp_capacity_kld": 100,
                "zld_compliance": True,
                "dg_set_kva": 500,
            },
            deficiency_notes=None,
            issue_date=date(2026, 1, 15),
            expiry_date=date(2031, 1, 14),
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        # Assertions
        assert doc.id is not None
        assert doc.business_id == biz.id
        assert doc.uploaded_by_user_id == user.id
        assert doc.requirement_id == req.id
        assert doc.document_type == DocumentType.ENVIRONMENTAL_MANAGEMENT_PLAN
        assert doc.verification_status == DocumentVerificationStatus.VERIFIED
        assert doc.file_size_bytes == 2048500
        assert doc.extracted_metadata["etp_capacity_kld"] == 100
        assert doc.issue_date == date(2026, 1, 15)
        assert doc.expiry_date == date(2031, 1, 14)


@pytest.mark.asyncio
async def test_document_storage_path_unique_constraint():
    """Verify duplicate storage paths raise an IntegrityError."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="admin@test.com",
            hashed_password="pw",
            full_name="Admin",
            role=UserRole.ADMIN,
        )
        session.add(user)
        await session.commit()

        biz = Business(
            user_id=user.id,
            legal_name="Test Enterprise",
            entity_type=EntityType.PRIVATE_LIMITED,
            pan="AAACT1234F",
        )
        session.add(biz)
        await session.commit()

        doc1 = Document(
            business_id=biz.id,
            document_type=DocumentType.PAN_CARD,
            file_name="pan1.pdf",
            storage_path="docs/pan.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            sha256_checksum="hash1",
        )
        session.add(doc1)
        await session.commit()

        # Duplicate storage path
        doc2 = Document(
            business_id=biz.id,
            document_type=DocumentType.PAN_CARD,
            file_name="pan2.pdf",
            storage_path="docs/pan.pdf",
            mime_type="application/pdf",
            file_size_bytes=2048,
            sha256_checksum="hash2",
        )
        session.add(doc2)
        with pytest.raises(IntegrityError):
            await session.commit()
