"""
Unit and API integration test suite for Personalized Roadmap Service (Fragment 54).
Validates milestone scheduling, forward pass date offsets, and roadmap API responses.
"""

from datetime import date
import pytest
from httpx import ASGITransport, AsyncClient
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import create_access_token
from app.main import app
from app.models.business import Business, EntityType, MSMECategory
from app.models.business_profile import BusinessProfile, IndustryScale, PollutionCategory
from app.models.user import User, UserRole
from app.services.requirement_engine import RequirementEngineService
from app.services.roadmap_service import RoadmapService


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def roadmap_fixtures():
    """Create owner user, business, profile, and seed requirements."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="promoter@solarex.in",
            hashed_password="SecurePassword123!",
            full_name="Vikramaditya Solarex",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        biz = Business(
            user_id=user.id,
            legal_name="Solarex Ingot Manufacturing Ltd",
            trade_name="Solarex",
            entity_type=EntityType.PUBLIC_LIMITED,
            msme_category=MSMECategory.LARGE,
            pan="AAACS8888P",
            gstin="27AAACS8888P1Z3",
        )
        session.add(biz)
        await session.commit()
        await session.refresh(biz)

        profile = BusinessProfile(
            business_id=biz.id,
            manufacturing_activity="Silicon ingot crystallization, wafer slicing, and chemical etching",
            industry_scale=IndustryScale.LARGE_SCALE,
            pollution_category=PollutionCategory.RED,
            land_area_sqm=9000.0,
            total_employees=200,
            plant_machinery_investment=220000000.0,
            power_requirement_kw=700.0,
            water_requirement_kld=55.0,
        )
        session.add(profile)
        await session.commit()

        # Seed catalog and generate requirements
        await RequirementEngineService.generate_requirements_for_business(session, biz.id)

        token = create_access_token({"sub": user.id, "role": user.role.value})
        return {"business_id": biz.id, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.mark.asyncio
async def test_roadmap_service_scheduling(roadmap_fixtures):
    """Verify RoadmapService computes valid forward pass start/finish offsets and milestones."""
    biz_id = roadmap_fixtures["business_id"]
    async with AsyncSessionLocal() as session:
        today = date.today()
        plan = await RoadmapService.generate_roadmap(session, biz_id, start_date=today)

        assert plan.business_id == biz_id
        assert plan.base_start_date == today
        assert plan.total_calendar_days >= 45
        assert len(plan.activities) >= 5
        assert len(plan.milestones) >= 2

        act_map = {a.approval_code: a for a in plan.activities}
        assert "CTE_PCB" in act_map
        assert "CTO_PCB" in act_map

        # CTO must start after or when CTE finishes
        cte_act = act_map["CTE_PCB"]
        cto_act = act_map["CTO_PCB"]
        assert cto_act.start_day_offset >= cte_act.finish_day_offset


@pytest.mark.asyncio
async def test_api_get_clearance_roadmap(roadmap_fixtures):
    """Verify GET /api/v1/approvals/roadmap/{business_id} endpoint."""
    biz_id = roadmap_fixtures["business_id"]
    headers = roadmap_fixtures["headers"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/approvals/roadmap/{biz_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["business_id"] == biz_id
        assert "base_start_date" in data
        assert "projected_commissioning_date" in data
        assert len(data["activities"]) >= 5
        assert len(data["milestones"]) >= 2
