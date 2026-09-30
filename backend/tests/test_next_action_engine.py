"""
Unit and integration test suite for Next-Action Recommendation Engine (Fragment 55).
Tests priority queue ranking, prerequisite unblocking progression, and REST API responses.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import create_access_token
from app.main import app
from app.models.approval import Approval
from app.models.approval_requirement import ApprovalRequirement, RequirementStatus
from app.models.business import Business, EntityType, MSMECategory
from app.models.business_profile import BusinessProfile, IndustryScale, PollutionCategory
from app.models.user import User, UserRole
from app.schemas.approval import ActionPriority, ActionType
from app.services.next_action_engine import NextActionEngineService
from app.services.requirement_engine import RequirementEngineService


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def enterprise_fixtures():
    """Create test enterprise, seed statutory requirements."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="promoter@bharatalloys.in",
            hashed_password="SecurePassword123!",
            full_name="Rajeshwar Alloy Promoter",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        biz = Business(
            user_id=user.id,
            legal_name="Bharat Special Alloys Ltd",
            trade_name="Bharat Alloys",
            entity_type=EntityType.PUBLIC_LIMITED,
            msme_category=MSMECategory.LARGE,
            pan="AAACB9999K",
            gstin="27AAACB9999K1Z4",
        )
        session.add(biz)
        await session.commit()
        await session.refresh(biz)

        profile = BusinessProfile(
            business_id=biz.id,
            manufacturing_activity="Electric arc furnace steel melting and alloy forging",
            industry_scale=IndustryScale.LARGE_SCALE,
            pollution_category=PollutionCategory.RED,
            land_area_sqm=12000.0,
            total_employees=250,
            plant_machinery_investment=300000000.0,
            power_requirement_kw=950.0,
            water_requirement_kld=70.0,
        )
        session.add(profile)
        await session.commit()

        await RequirementEngineService.generate_requirements_for_business(session, biz.id)

        token = create_access_token({"sub": user.id, "role": user.role.value})
        return {"business_id": biz.id, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.mark.asyncio
async def test_next_action_engine_initial_state(enterprise_fixtures):
    """Test that initially, critical clearances are APPLY_NOW and dependent clearances are BLOCKED."""
    biz_id = enterprise_fixtures["business_id"]

    async with AsyncSessionLocal() as session:
        summary = await NextActionEngineService.compute_next_actions(session, biz_id)

        assert summary.business_id == biz_id
        assert summary.total_clearances >= 5
        assert summary.ready_to_act_count >= 1
        assert summary.blocked_count >= 1
        assert summary.top_immediate_action is not None
        assert summary.top_immediate_action.priority in (ActionPriority.CRITICAL, ActionPriority.HIGH)

        action_map = {a.approval_code: a for a in summary.actions}
        assert "CTE_PCB" in action_map
        assert "CTO_PCB" in action_map

        # CTE should be unlocked and ready to apply
        cte_action = action_map["CTE_PCB"]
        assert cte_action.is_unlocked is True
        assert cte_action.action_type == ActionType.APPLY_NOW
        assert cte_action.is_critical_path is True
        assert cte_action.priority == ActionPriority.CRITICAL

        # CTO must be blocked by CTE
        cto_action = action_map["CTO_PCB"]
        assert cto_action.is_unlocked is False
        assert cto_action.action_type == ActionType.RESOLVE_PREREQUISITES
        assert "CTE_PCB" in cto_action.blocked_by


@pytest.mark.asyncio
async def test_next_action_engine_prerequisite_unlock_progression(enterprise_fixtures):
    """Verify that approving a prerequisite transitions dependent clearance from BLOCKED to UNLOCKED."""
    biz_id = enterprise_fixtures["business_id"]

    async with AsyncSessionLocal() as session:
        # Fetch CTE requirement and mark as APPROVED
        stmt = (
            select(ApprovalRequirement)
            .join(Approval, ApprovalRequirement.approval_id == Approval.id)
            .where(
                ApprovalRequirement.business_id == biz_id,
                Approval.code == "CTE_PCB",
            )
        )
        cte_req = (await session.execute(stmt)).scalar_one()
        cte_req.status = RequirementStatus.APPROVED
        await session.commit()

        # Recompute actions
        summary = await NextActionEngineService.compute_next_actions(session, biz_id)
        action_map = {a.approval_code: a for a in summary.actions}

        # CTE is now DOWNLOAD_CERTIFICATE
        cte_action = action_map["CTE_PCB"]
        assert cte_action.action_type == ActionType.DOWNLOAD_CERTIFICATE
        assert cte_action.priority == ActionPriority.LOW

        # CTO should now be unblocked!
        cto_action = action_map["CTO_PCB"]
        assert cto_action.is_unlocked is True
        assert cto_action.action_type == ActionType.APPLY_NOW
        assert cto_action.priority in (ActionPriority.CRITICAL, ActionPriority.HIGH)


@pytest.mark.asyncio
async def test_api_get_next_clearance_actions(enterprise_fixtures):
    """Verify GET /api/v1/approvals/next-actions/{business_id} REST endpoint."""
    biz_id = enterprise_fixtures["business_id"]
    headers = enterprise_fixtures["headers"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/approvals/next-actions/{biz_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["business_id"] == biz_id
        assert data["total_clearances"] >= 5
        assert "ready_to_act_count" in data
        assert "top_immediate_action" in data
        assert data["top_immediate_action"]["approval_code"] == "CTE_PCB"
        assert len(data["actions"]) >= 5
