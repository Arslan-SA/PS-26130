"""
Unit and API integration tests for Approval Checklist catalog & endpoints (Fragment 48).
Validates statutory checklist retrieval, category partitioning, and requirement binding.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import create_access_token
from app.main import app
from app.models.approval import Approval
from app.models.approval_requirement import ApprovalRequirement, RequirementStage, RequirementStatus
from app.models.business import Business, EntityType, MSMECategory
from app.models.user import User, UserRole
from app.services.approval_checklist import get_approval_checklist


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def sample_user_and_requirement():
    """Create user, business, approval, and requirement instance."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="promoter@chemcorp.in",
            hashed_password="SecurePassword123!",
            full_name="Vikram Seth",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        biz = Business(
            user_id=user.id,
            legal_name="ChemCorp Agro Chemicals Ltd",
            trade_name="ChemCorp",
            entity_type=EntityType.PUBLIC_LIMITED,
            msme_category=MSMECategory.LARGE,
            pan="AAACC1111Q",
            gstin="27AAACC1111Q1Z1",
        )
        session.add(biz)

        appr = Approval(
            code="CTE_PCB",
            title="Consent to Establish (CTE) under Water & Air Acts",
            department_code="SPCB",
            issuing_authority="State Pollution Control Board",
            sla_days=45,
            estimated_fee_base=50000.0,
        )
        session.add(appr)
        await session.commit()
        await session.refresh(biz)
        await session.refresh(appr)

        req = ApprovalRequirement(
            business_id=biz.id,
            approval_id=appr.id,
            status=RequirementStatus.NOT_STARTED,
            stage=RequirementStage.PRE_ESTABLISHMENT,
            priority=1,
            is_mandatory=True,
            trigger_reason="Red category unit requires CTE prior to construction.",
            estimated_fee=50000.0,
            sla_deadline_days=45,
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)

        token = create_access_token({"sub": user.id, "role": user.role.value})
        return {"user": user, "req": req, "headers": {"Authorization": f"Bearer {token}"}}


def test_service_get_approval_checklist():
    """Verify service returns complete checklist with forms, documents, and inspections."""
    cte_chk = get_approval_checklist("CTE_PCB")
    assert cte_chk is not None
    assert cte_chk.approval_code == "CTE_PCB"
    assert len(cte_chk.items) == 8

    categories = {it.category for it in cte_chk.items}
    assert {"FORM", "DOCUMENT", "PREREQUISITE", "INSPECTION"}.issubset(categories)


@pytest.mark.asyncio
async def test_api_get_checklist_by_code(sample_user_and_requirement):
    """Verify GET /api/v1/approvals/{approval_code}/checklist endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/approvals/CTE_PCB/checklist",
            headers=sample_user_and_requirement["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["approval_code"] == "CTE_PCB"
        assert len(data["items"]) == 8


@pytest.mark.asyncio
async def test_api_get_checklist_for_requirement(sample_user_and_requirement):
    """Verify GET /api/v1/approvals/requirements/{requirement_id}/checklist endpoint."""
    req = sample_user_and_requirement["req"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/approvals/requirements/{req.id}/checklist",
            headers=sample_user_and_requirement["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["approval_code"] == "CTE_PCB"
        assert len(data["items"]) == 8
