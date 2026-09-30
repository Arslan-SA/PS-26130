"""
Unit and integration test suite for Approval Status Tracking & Audit (Fragment 56).
Validates lifecycle transitions, immutable audit logs, reference numbers, and history REST APIs.
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
from app.services.requirement_engine import RequirementEngineService
from app.services.status_tracking_service import StatusTrackingService


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def tracking_fixtures():
    """Create test enterprise, seed statutory requirements."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="director@apexheavy.in",
            hashed_password="SecurePassword123!",
            full_name="Col. Vikramaditya Apex",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        biz = Business(
            user_id=user.id,
            legal_name="Apex Heavy Castings Ltd",
            trade_name="Apex Castings",
            entity_type=EntityType.PUBLIC_LIMITED,
            msme_category=MSMECategory.LARGE,
            pan="AAACA1111B",
            gstin="27AAACA1111B1Z2",
        )
        session.add(biz)
        await session.commit()
        await session.refresh(biz)

        profile = BusinessProfile(
            business_id=biz.id,
            manufacturing_activity="Heavy iron foundry and grey alloy casting",
            industry_scale=IndustryScale.LARGE_SCALE,
            pollution_category=PollutionCategory.RED,
            land_area_sqm=15000.0,
            total_employees=300,
            plant_machinery_investment=450000000.0,
            power_requirement_kw=1200.0,
            water_requirement_kld=85.0,
        )
        session.add(profile)
        await session.commit()

        reqs = await RequirementEngineService.generate_requirements_for_business(session, biz.id)

        token = create_access_token({"sub": user.id, "role": user.role.value})
        return {
            "user_id": user.id,
            "business_id": biz.id,
            "requirements": reqs,
            "headers": {"Authorization": f"Bearer {token}"},
        }


@pytest.mark.asyncio
async def test_status_tracking_service_transitions(tracking_fixtures):
    """Test recording multiple chronological status transitions with remarks and references."""
    user_id = tracking_fixtures["user_id"]
    req = tracking_fixtures["requirements"][0]

    async with AsyncSessionLocal() as session:
        # 1. NOT_STARTED -> IN_PROGRESS
        req1, h1 = await StatusTrackingService.record_status_transition(
            session=session,
            requirement_id=req.id,
            to_status=RequirementStatus.IN_PROGRESS,
            user_id=user_id,
            remarks="Filing initiated on State Single Window System.",
            reference_number="DRAFT-2026-001",
        )
        assert req1.status == RequirementStatus.IN_PROGRESS
        assert h1.from_status == RequirementStatus.NOT_STARTED
        assert h1.to_status == RequirementStatus.IN_PROGRESS
        assert h1.reference_number == "DRAFT-2026-001"
        assert h1.changed_by_user_id == user_id

        # 2. IN_PROGRESS -> SUBMITTED
        req2, h2 = await StatusTrackingService.record_status_transition(
            session=session,
            requirement_id=req.id,
            to_status=RequirementStatus.SUBMITTED,
            user_id=user_id,
            remarks="Application fee paid and documents uploaded.",
            reference_number="ACK-PCB-2026-8889",
        )
        assert req2.status == RequirementStatus.SUBMITTED
        assert h2.from_status == RequirementStatus.IN_PROGRESS
        assert h2.to_status == RequirementStatus.SUBMITTED
        assert h2.reference_number == "ACK-PCB-2026-8889"

        # 3. Retrieve history
        history = await StatusTrackingService.get_history_for_requirement(session, req.id)
        assert len(history) == 2
        assert history[0].to_status == RequirementStatus.SUBMITTED
        assert history[1].to_status == RequirementStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_api_status_update_and_history_retrieval(tracking_fixtures):
    """Test PATCH status endpoint, requirement history endpoint, and business history endpoint."""
    biz_id = tracking_fixtures["business_id"]
    headers = tracking_fixtures["headers"]
    req = tracking_fixtures["requirements"][0]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Update status via API
        patch_payload = {
            "status": "SUBMITTED",
            "remarks": "Filing uploaded via UdyamSetu unified gateway.",
            "reference_number": "REG-2026-10101",
            "notes": "Fast-track scrutiny requested under MSME Act.",
        }
        patch_resp = await client.patch(
            f"/api/v1/approvals/requirements/{req.id}/status",
            json=patch_payload,
            headers=headers,
        )
        assert patch_resp.status_code == 200
        patch_data = patch_resp.json()
        assert patch_data["status"] == "SUBMITTED"
        assert patch_data["notes"] == "Fast-track scrutiny requested under MSME Act."

        # 2. Retrieve history for requirement
        hist_resp = await client.get(
            f"/api/v1/approvals/requirements/{req.id}/history",
            headers=headers,
        )
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert len(hist_data) == 1
        assert hist_data[0]["to_status"] == "SUBMITTED"
        assert hist_data[0]["reference_number"] == "REG-2026-10101"
        assert hist_data[0]["remarks"] == "Filing uploaded via UdyamSetu unified gateway."

        # 3. Retrieve enterprise-wide business history
        biz_hist_resp = await client.get(
            f"/api/v1/approvals/history/{biz_id}",
            headers=headers,
        )
        assert biz_hist_resp.status_code == 200
        biz_hist_data = biz_hist_resp.json()
        assert len(biz_hist_data) >= 1
        assert biz_hist_data[0]["business_id"] == biz_id
