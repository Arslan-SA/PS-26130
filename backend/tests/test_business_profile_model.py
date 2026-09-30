"""
Tests for BusinessProfile domain model and relationship with Business entity.
"""

from datetime import date
import pytest
from sqlalchemy import select
from app.core.database import engine, Base, AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.business import Business, EntityType, MSMECategory
from app.models.business_profile import BusinessProfile, IndustryScale, PollutionCategory


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def test_business_profile_instantiation():
    """Verify BusinessProfile initialization and attributes."""
    profile = BusinessProfile(
        business_id="biz-1234-uuid",
        nic_code="20111",
        manufacturing_activity="Manufacture of basic chemicals",
        products_services="Industrial organic chemicals and solvents",
        industry_scale=IndustryScale.MEDIUM_SCALE,
        pollution_category=PollutionCategory.RED,
        state="Maharashtra",
        district="Pune",
        city="Pune",
        pincode="411001",
        full_address="Plot 42, MIDC Bhosari Industrial Area",
        plot_number="Plot 42",
        industrial_area="Bhosari MIDC",
        latitude=18.627,
        longitude=73.847,
        total_employees=85,
        plant_machinery_investment=25000000.0,
        land_area_sqm=5000.0,
        annual_turnover=80000000.0,
        power_requirement_kw=350.0,
        water_requirement_kld=50.0,
        contact_person="Rajesh Kumar",
        contact_phone="+919876543210",
        contact_email="rajesh@chemtech.example.com",
        profile_completeness=85,
        is_profile_complete=False,
    )

    assert profile.business_id == "biz-1234-uuid"
    assert profile.nic_code == "20111"
    assert profile.industry_scale == IndustryScale.MEDIUM_SCALE
    assert profile.pollution_category == PollutionCategory.RED
    assert profile.state == "Maharashtra"
    assert profile.district == "Pune"
    assert profile.pincode == "411001"
    assert profile.total_employees == 85
    assert profile.plant_machinery_investment == 25000000.0
    assert profile.power_requirement_kw == 350.0
    assert profile.water_requirement_kld == 50.0
    assert profile.profile_completeness == 85
    assert profile.is_profile_complete is False


def test_business_profile_defaults():
    """Verify BusinessProfile defaults."""
    profile = BusinessProfile(
        business_id="biz-test-uuid",
    )

    assert profile.industry_scale == IndustryScale.SMALL_SCALE
    assert profile.pollution_category is None
    assert profile.profile_completeness == 0
    assert profile.is_profile_complete is False
    assert repr(profile) == "<BusinessProfile business_id=biz-test-uuid nic=None>"


@pytest.mark.asyncio
async def test_business_and_profile_relationship():
    """Verify Business and BusinessProfile 1-to-1 relationship with DB persistence."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="founder@greenenergy.in",
            hashed_password="hashed_pw_test",
            full_name="Pooja Sharma",
            role=UserRole.INDUSTRY_USER,
        )
        session.add(user)
        await session.flush()

        business = Business(
            user_id=user.id,
            legal_name="Green Energy Solutions Pvt Ltd",
            trade_name="GreenEnergy",
            entity_type=EntityType.PRIVATE_LIMITED,
            pan="ABCDE1234F",
            gstin="27ABCDE1234F1Z5",
            udyam_number="UDYAM-MH-02-0012345",
            msme_category=MSMECategory.SMALL,
            incorporation_date=date(2021, 6, 1),
        )
        session.add(business)
        await session.flush()

        profile = BusinessProfile(
            business_id=business.id,
            nic_code="27101",
            manufacturing_activity="Solar Panel Assembly & Inverters",
            industry_scale=IndustryScale.SMALL_SCALE,
            pollution_category=PollutionCategory.GREEN,
            state="Maharashtra",
            district="Nashik",
            city="Nashik",
            pincode="422007",
            total_employees=40,
            plant_machinery_investment=15000000.0,
            profile_completeness=100,
            is_profile_complete=True,
        )
        session.add(profile)
        await session.commit()

        # Query Business with loaded profile
        stmt = select(Business).where(Business.id == business.id)
        result = await session.execute(stmt)
        saved_biz = result.scalar_one()

        assert saved_biz.profile is not None
        assert saved_biz.profile.nic_code == "27101"
        assert saved_biz.profile.pollution_category == PollutionCategory.GREEN
        assert saved_biz.profile.is_profile_complete is True
        assert saved_biz.profile.business.legal_name == "Green Energy Solutions Pvt Ltd"
