"""
Unit tests for ApprovalRequirement domain model (Fragment 42).
Validates business-to-clearance binding, status transitions, constraints, and cascading integrity.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.approval import Approval
from app.models.approval_requirement import ApprovalRequirement, RequirementStage, RequirementStatus
from app.models.business import Business, EntityType, MSMECategory
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def sample_fixtures():
    """Create sample User, Business, and Approval records for requirement testing."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="promoter@greensteel.in",
            hashed_password="SecurePassword123!",
            full_name="Rajiv Bajaj",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        business = Business(
            user_id=user.id,
            legal_name="GreenSteel Manufacturing Private Limited",
            trade_name="GreenSteel Eco",
            entity_type=EntityType.PRIVATE_LIMITED,
            msme_category=MSMECategory.MEDIUM,
            pan="AAACG9876K",
            gstin="27AAACG9876K1Z9",
        )
        session.add(business)

        approval = Approval(
            code="CTE_SPCB",
            title="Consent to Establish (Water/Air Acts)",
            department_code="SPCB",
            issuing_authority="State Pollution Control Board",
            sla_days=45,
            estimated_fee_base=50000.0,
        )
        session.add(approval)
        await session.commit()
        await session.refresh(business)
        await session.refresh(approval)

        return business, approval


@pytest.mark.asyncio
async def test_create_approval_requirement(sample_fixtures):
    """Verify that an ApprovalRequirement record can be successfully persisted and linked."""
    business, approval = sample_fixtures
    async with AsyncSessionLocal() as session:
        req = ApprovalRequirement(
            business_id=business.id,
            approval_id=approval.id,
            status=RequirementStatus.NOT_STARTED,
            stage=RequirementStage.PRE_ESTABLISHMENT,
            priority=1,
            is_mandatory=True,
            trigger_reason="Red category classification requires CTE prior to foundation work.",
            estimated_fee=75000.0,
            sla_deadline_days=45,
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)

        assert req.id is not None
        assert req.business_id == business.id
        assert req.approval_id == approval.id
        assert req.status == RequirementStatus.NOT_STARTED
        assert req.stage == RequirementStage.PRE_ESTABLISHMENT
        assert req.estimated_fee == 75000.0
        assert "<ApprovalRequirement" in repr(req)


@pytest.mark.asyncio
async def test_duplicate_requirement_constraint(sample_fixtures):
    """Verify that an enterprise cannot have duplicate requirements for the same approval."""
    business, approval = sample_fixtures
    async with AsyncSessionLocal() as session:
        req1 = ApprovalRequirement(
            business_id=business.id,
            approval_id=approval.id,
            trigger_reason="First identification",
        )
        session.add(req1)
        await session.commit()

        req2 = ApprovalRequirement(
            business_id=business.id,
            approval_id=approval.id,
            trigger_reason="Duplicate identification",
        )
        session.add(req2)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_requirement_status_transition(sample_fixtures):
    """Verify requirement status can transition through the compliance lifecycle."""
    business, approval = sample_fixtures
    async with AsyncSessionLocal() as session:
        req = ApprovalRequirement(
            business_id=business.id,
            approval_id=approval.id,
            trigger_reason="Standard lifecycle progression",
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)

        # Transition to IN_PROGRESS
        req.status = RequirementStatus.IN_PROGRESS
        await session.commit()
        await session.refresh(req)
        assert req.status == RequirementStatus.IN_PROGRESS

        # Transition to APPROVED
        req.status = RequirementStatus.APPROVED
        await session.commit()
        await session.refresh(req)
        assert req.status == RequirementStatus.APPROVED
