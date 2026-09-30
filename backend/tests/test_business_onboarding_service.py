"""
Tests for Business Onboarding Service and lifecycle orchestration.
"""

from datetime import date
import pytest
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.exceptions import ConflictError, AuthorizationError
from app.models.business import EntityType, MSMECategory
from app.models.business_profile import IndustryScale, PollutionCategory
from app.models.user import User, UserRole
from app.schemas.business import (
    BusinessCreate,
    BusinessProfileCreate,
    BusinessProfileUpdate,
    BusinessUpdate,
    OnboardingRequest,
)
from app.services.business_service import (
    get_business_by_id,
    get_user_businesses,
    onboard_business,
    update_business,
    update_business_profile,
)


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_onboard_business_success():
    """Verify onboarding creates business and operational profile with calculated completeness."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="promoter@solarpower.com",
            hashed_password="pw_hash_test",
            full_name="Vikram Mehta",
            role=UserRole.INDUSTRY_USER,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        request = OnboardingRequest(
            business=BusinessCreate(
                legal_name="Solar Power Technologies Private Limited",
                trade_name="SolarTech",
                entity_type=EntityType.PRIVATE_LIMITED,
                pan="ABCDE5678F",
                gstin="27ABCDE5678F1Z2",
                udyam_number="UDYAM-MH-01-0088888",
                msme_category=MSMECategory.SMALL,
                incorporation_date=date(2022, 1, 15),
            ),
            profile=BusinessProfileCreate(
                nic_code="27101",
                manufacturing_activity="Manufacture of solar PV cells and modules",
                products_services="Solar panels, inverters, storage batteries",
                industry_scale=IndustryScale.SMALL_SCALE,
                pollution_category=PollutionCategory.GREEN,
                state="Maharashtra",
                district="Pune",
                pincode="411019",
                full_address="Chakan Industrial Area Phase II, Pune",
                total_employees=45,
                plant_machinery_investment=45000000.0,
                annual_turnover=90000000.0,
                power_requirement_kw=200.0,
                water_requirement_kld=25.0,
                contact_person="Vikram Mehta",
                contact_phone="+919876543210",
            ),
        )

        business, next_steps = await onboard_business(session, user, request)

        assert business.id is not None
        assert business.legal_name == "Solar Power Technologies Private Limited"
        assert business.pan == "ABCDE5678F"
        assert business.profile is not None
        assert business.profile.nic_code == "27101"
        assert business.profile.pollution_category == PollutionCategory.GREEN
        assert business.profile.profile_completeness >= 80
        assert business.profile.is_profile_complete is True
        assert len(next_steps) > 0


@pytest.mark.asyncio
async def test_onboard_business_duplicate_pan():
    """Verify duplicate PAN raises ConflictError."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="user1@example.com",
            hashed_password="pw_hash_test",
            full_name="User One",
            role=UserRole.INDUSTRY_USER,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        request = OnboardingRequest(
            business=BusinessCreate(
                legal_name="First Corp Pvt Ltd",
                pan="DUPLICATE1",
            ),
        )
        await onboard_business(session, user, request)

        # Attempt to onboard another enterprise with the same PAN
        with pytest.raises(ConflictError) as exc_info:
            await onboard_business(session, user, request)
        assert "already registered" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_business_ownership_authorization():
    """Verify other industry users cannot access or alter an enterprise profile."""
    async with AsyncSessionLocal() as session:
        user1 = User(email="owner@alpha.com", hashed_password="pw", full_name="Owner Alpha", role=UserRole.INDUSTRY_USER)
        user2 = User(email="intruder@beta.com", hashed_password="pw", full_name="Intruder Beta", role=UserRole.INDUSTRY_USER)
        session.add_all([user1, user2])
        await session.commit()

        request = OnboardingRequest(
            business=BusinessCreate(legal_name="Alpha Corp", pan="ALPHA1234K")
        )
        business, _ = await onboard_business(session, user1, request)

        # Intruder attempts to fetch business
        with pytest.raises(AuthorizationError):
            await get_business_by_id(session, business.id, user2)

        # Owner can fetch
        fetched = await get_business_by_id(session, business.id, user1)
        assert fetched.id == business.id


@pytest.mark.asyncio
async def test_update_business_and_profile():
    """Verify updating business info and operational profile."""
    async with AsyncSessionLocal() as session:
        user = User(email="owner@delta.com", hashed_password="pw", full_name="Owner Delta", role=UserRole.INDUSTRY_USER)
        session.add(user)
        await session.commit()

        request = OnboardingRequest(
            business=BusinessCreate(legal_name="Delta Initial", pan="DELTA1234D")
        )
        business, _ = await onboard_business(session, user, request)

        # Update business legal name
        updated_biz = await update_business(
            session,
            business.id,
            BusinessUpdate(trade_name="Delta Brand"),
            user,
        )
        assert updated_biz.trade_name == "Delta Brand"

        # Update profile
        updated_profile = await update_business_profile(
            session,
            business.id,
            BusinessProfileUpdate(
                nic_code="10101",
                state="Gujarat",
                district="Ahmedabad",
                pincode="380001",
            ),
            user,
        )
        assert updated_profile.nic_code == "10101"
        assert updated_profile.state == "Gujarat"
        assert updated_profile.profile_completeness > 0
