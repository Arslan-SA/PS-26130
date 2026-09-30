"""
Unit tests for Statutory Requirement Discovery & Synchronization Engine (Fragment 45).
Validates automated clearance mapping, database catalog seeding, idempotency, and composite analytics.
"""

import pytest
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.approval import Approval
from app.models.approval_requirement import ApprovalRequirement, RequirementStage, RequirementStatus
from app.models.business import Business, EntityType, MSMECategory
from app.models.business_profile import BusinessProfile, IndustryScale, PollutionCategory
from app.models.department import Department
from app.models.user import User, UserRole
from app.services.requirement_engine import RequirementEngineService


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def sample_business():
    """Create a sample user, business, and operational profile in the database."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="founder@indiapolymer.com",
            hashed_password="SecurePassword123!",
            full_name="Anil Singhal",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        business = Business(
            user_id=user.id,
            legal_name="India Polymer Chemicals Limited",
            trade_name="IPC Ltd",
            entity_type=EntityType.PUBLIC_LIMITED,
            msme_category=MSMECategory.LARGE,
            pan="AAACI5432P",
            gstin="27AAACI5432P1Z4",
        )
        session.add(business)
        await session.commit()
        await session.refresh(business)

        profile = BusinessProfile(
            business_id=business.id,
            manufacturing_activity="Polymer synthesis, organic chemical resins, and industrial coatings",
            industry_scale=IndustryScale.LARGE_SCALE,
            pollution_category=PollutionCategory.RED,
            state="Maharashtra",
            district="Raigad",
            pincode="402116",
            land_area_sqm=6500.0,
            total_employees=150,
            plant_machinery_investment=120000000.0,  # 12 Cr
            power_requirement_kw=400.0,              # 400 kW > 50 kW
            water_requirement_kld=35.0,              # 35 KLD >= 10 KLD
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

        return business, profile


@pytest.mark.asyncio
async def test_seed_default_catalog():
    """Verify that default departments and statutory approvals are seeded idempotently."""
    async with AsyncSessionLocal() as session:
        await RequirementEngineService.seed_default_catalog(session)

        # Verify departments
        stmt_d = select(Department)
        depts = (await session.execute(stmt_d)).scalars().all()
        assert len(depts) == 5
        dept_codes = {d.code for d in depts}
        assert {"SPCB", "FIRE", "DISH", "DISCOM", "CGWA"}.issubset(dept_codes)

        # Verify approvals
        stmt_a = select(Approval)
        apps = (await session.execute(stmt_a)).scalars().all()
        assert len(apps) == 6
        app_codes = {a.code for a in apps}
        assert {"CTE_PCB", "CTO_PCB", "FIRE_NOC", "POWER_HT", "FACTORY_LIC", "CGWA_GW"}.issubset(app_codes)

        # Idempotent re-seed
        await RequirementEngineService.seed_default_catalog(session)
        apps_after = (await session.execute(stmt_a)).scalars().all()
        assert len(apps_after) == 6


@pytest.mark.asyncio
async def test_generate_requirements_for_business(sample_business):
    """Verify automated generation and database persistence of requirements for a Red unit."""
    business, profile = sample_business
    async with AsyncSessionLocal() as session:
        reqs = await RequirementEngineService.generate_requirements_for_business(session, business.id)

        assert len(reqs) == 6
        assert all(r.status == RequirementStatus.NOT_STARTED for r in reqs)
        assert all(r.is_mandatory for r in reqs)

        # Re-run generation to test idempotency
        reqs_rerun = await RequirementEngineService.generate_requirements_for_business(session, business.id)
        assert len(reqs_rerun) == 6

        # Check in DB
        stmt = select(ApprovalRequirement).where(ApprovalRequirement.business_id == business.id)
        db_reqs = (await session.execute(stmt)).scalars().all()
        assert len(db_reqs) == 6


@pytest.mark.asyncio
async def test_status_preservation_on_reevaluation(sample_business):
    """Verify that existing user progress (e.g. SUBMITTED) is preserved when rules re-run."""
    business, profile = sample_business
    async with AsyncSessionLocal() as session:
        reqs = await RequirementEngineService.generate_requirements_for_business(session, business.id)
        
        # User submits CTE clearance
        cte_req = reqs[0]
        cte_req.status = RequirementStatus.SUBMITTED
        await session.commit()

        # Re-run requirement generation
        reqs_after = await RequirementEngineService.generate_requirements_for_business(session, business.id)
        cte_after = next(r for r in reqs_after if r.id == cte_req.id)
        assert cte_after.status == RequirementStatus.SUBMITTED


@pytest.mark.asyncio
async def test_get_business_clearance_summary(sample_business):
    """Verify composite fee calculation, stage breakdown, and critical path metrics."""
    business, profile = sample_business
    async with AsyncSessionLocal() as session:
        await RequirementEngineService.generate_requirements_for_business(session, business.id)

        summary = await RequirementEngineService.get_business_clearance_summary(session, business.id)

        assert summary["business_id"] == business.id
        assert summary["total_requirements"] == 6
        assert summary["mandatory_requirements"] == 6
        assert summary["total_estimated_fee"] > 150000.0  # Combined fees
        assert summary["pre_establishment_critical_days"] == 45  # Max of CTE (45) / FIRE (21) / CGWA (45)
        assert summary["by_stage"][RequirementStage.PRE_ESTABLISHMENT.value] == 3
        assert summary["by_department"]["SPCB"] == 2
        assert summary["by_department"]["FIRE"] == 1
