"""
Integration test suite for Statutory Approval Recommendation REST APIs (Fragment 46).
Tests discovery execution, requirement listing, RBAC ownership protection, and status updates.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import create_access_token
from app.main import app
from app.models.approval_requirement import RequirementStage, RequirementStatus
from app.models.business import Business, EntityType, MSMECategory
from app.models.business_profile import BusinessProfile, IndustryScale, PollutionCategory
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def api_fixtures():
    """Create owner user, competitor user, business, and profile."""
    async with AsyncSessionLocal() as session:
        owner = User(
            email="promoter@solarenergy.in",
            hashed_password="SecurePassword123!",
            full_name="Sunil Mehta",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        intruder = User(
            email="intruder@rival.in",
            hashed_password="SecurePassword123!",
            full_name="Intruder User",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        officer = User(
            email="officer@spcb.gov.in",
            hashed_password="SecurePassword123!",
            full_name="Officer Deshmukh",
            role=UserRole.DEPARTMENT_OFFICER,
            department_id="SPCB",
            is_active=True,
            is_verified=True,
        )
        session.add_all([owner, intruder, officer])
        await session.commit()
        await session.refresh(owner)
        await session.refresh(intruder)
        await session.refresh(officer)

        business = Business(
            user_id=owner.id,
            legal_name="Apex Chemicals and Fertilizers Ltd",
            trade_name="Apex Chem",
            entity_type=EntityType.PUBLIC_LIMITED,
            msme_category=MSMECategory.LARGE,
            pan="AAACA1234F",
            gstin="27AAACA1234F1Z5",
        )
        session.add(business)
        await session.commit()
        await session.refresh(business)

        profile = BusinessProfile(
            business_id=business.id,
            manufacturing_activity="Inorganic chemicals and fertilizer synthesis",
            industry_scale=IndustryScale.LARGE_SCALE,
            pollution_category=PollutionCategory.RED,
            land_area_sqm=8000.0,
            total_employees=180,
            plant_machinery_investment=250000000.0,
            power_requirement_kw=600.0,
            water_requirement_kld=50.0,
        )
        session.add(profile)
        await session.commit()

        owner_token = create_access_token({"sub": owner.id, "role": owner.role.value})
        intruder_token = create_access_token({"sub": intruder.id, "role": intruder.role.value})
        officer_token = create_access_token({"sub": officer.id, "role": officer.role.value})

        return {
            "business_id": business.id,
            "owner_headers": {"Authorization": f"Bearer {owner_token}"},
            "intruder_headers": {"Authorization": f"Bearer {intruder_token}"},
            "officer_headers": {"Authorization": f"Bearer {officer_token}"},
        }


@pytest.mark.asyncio
async def test_discover_approvals_success(api_fixtures):
    """Verify executing discovery returns requirements and summary metrics."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/approvals/discover/{api_fixtures['business_id']}",
            headers=api_fixtures["owner_headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["business_id"] == api_fixtures["business_id"]
        assert data["count"] == 6
        assert len(data["requirements"]) == 6
        assert data["summary"]["mandatory_requirements"] == 6
        assert data["summary"]["total_estimated_fee"] > 0


@pytest.mark.asyncio
async def test_discover_approvals_rbac_rejection(api_fixtures):
    """Verify another industry user cannot access or trigger discovery for someone else's business."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/approvals/discover/{api_fixtures['business_id']}",
            headers=api_fixtures["intruder_headers"],
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_officer_can_view_and_summary(api_fixtures):
    """Verify department officer can access discovery and summary endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Discover as officer
        disc_resp = await client.post(
            f"/api/v1/approvals/discover/{api_fixtures['business_id']}",
            headers=api_fixtures["officer_headers"],
        )
        assert disc_resp.status_code == 200

        # 2. Get summary
        sum_resp = await client.get(
            f"/api/v1/approvals/summary/{api_fixtures['business_id']}",
            headers=api_fixtures["officer_headers"],
        )
        assert sum_resp.status_code == 200
        summary = sum_resp.json()
        assert summary["total_requirements"] == 6
        assert summary["pre_establishment_critical_days"] == 45


@pytest.mark.asyncio
async def test_update_requirement_status(api_fixtures):
    """Verify updating requirement status and notes."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Discover first
        disc_resp = await client.post(
            f"/api/v1/approvals/discover/{api_fixtures['business_id']}",
            headers=api_fixtures["owner_headers"],
        )
        req_id = disc_resp.json()["requirements"][0]["id"]

        # Update status
        patch_resp = await client.patch(
            f"/api/v1/approvals/requirements/{req_id}/status",
            headers=api_fixtures["owner_headers"],
            json={"status": "IN_PROGRESS", "notes": "Application dossier in drafting."},
        )
        assert patch_resp.status_code == 200
        updated = patch_resp.json()
        assert updated["status"] == "IN_PROGRESS"
        assert updated["notes"] == "Application dossier in drafting."


@pytest.mark.asyncio
async def test_get_requirement_by_id(api_fixtures):
    """Verify retrieving a specific approval requirement by ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        disc_resp = await client.post(
            f"/api/v1/approvals/discover/{api_fixtures['business_id']}",
            headers=api_fixtures["owner_headers"],
        )
        req_id = disc_resp.json()["requirements"][0]["id"]

        get_resp = await client.get(
            f"/api/v1/approvals/requirements/{req_id}",
            headers=api_fixtures["owner_headers"],
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == req_id
        assert "approval" in data
        assert data["approval"]["code"] is not None

