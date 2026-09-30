"""
Unit tests for Department domain model (Fragment 43).
Validates regulatory authority catalog, jurisdiction hierarchies, unique codes, and SLA configurations.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.department import Department, JurisdictionLevel


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_create_department_with_defaults():
    """Verify that a statutory Department record can be created with default attributes."""
    async with AsyncSessionLocal() as session:
        dept = Department(
            code="SPCB_MH",
            name="Maharashtra Pollution Control Board",
            jurisdiction_level=JurisdictionLevel.STATE,
            state="Maharashtra",
            nodal_officer_name="Shri P. Anbalagan, IAS",
            nodal_officer_email="ms@mpcb.gov.in",
            nodal_officer_phone="+912224010437",
            website_portal="https://mpcb.gov.in",
            grievance_portal="https://mpcb.gov.in/grievance",
            standard_sla_days=45,
            description="State environmental statutory authority enforcing Air, Water, and Waste Rules.",
        )
        session.add(dept)
        await session.commit()
        await session.refresh(dept)

        assert dept.id is not None
        assert dept.code == "SPCB_MH"
        assert dept.jurisdiction_level == JurisdictionLevel.STATE
        assert dept.standard_sla_days == 45
        assert "<Department code='SPCB_MH'" in repr(dept)


@pytest.mark.asyncio
async def test_department_unique_code():
    """Verify that department codes are strictly unique across the registry."""
    async with AsyncSessionLocal() as session:
        dept1 = Department(
            code="FIRE_DELHI",
            name="Delhi Fire Service",
            jurisdiction_level=JurisdictionLevel.STATE,
            state="Delhi",
        )
        session.add(dept1)
        await session.commit()

        dept2 = Department(
            code="FIRE_DELHI",
            name="Duplicate Fire Department",
            jurisdiction_level=JurisdictionLevel.STATE,
            state="Delhi",
        )
        session.add(dept2)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_filter_departments_by_jurisdiction():
    """Verify filtering departments between Central and State jurisdictions."""
    async with AsyncSessionLocal() as session:
        departments = [
            Department(
                code="PESO",
                name="Petroleum and Explosives Safety Organisation",
                jurisdiction_level=JurisdictionLevel.CENTRAL,
            ),
            Department(
                code="CGWA",
                name="Central Ground Water Authority",
                jurisdiction_level=JurisdictionLevel.CENTRAL,
            ),
            Department(
                code="DISH_GJ",
                name="Directorate of Industrial Safety and Health Gujarat",
                jurisdiction_level=JurisdictionLevel.STATE,
                state="Gujarat",
            ),
        ]
        session.add_all(departments)
        await session.commit()

        stmt = select(Department).where(Department.jurisdiction_level == JurisdictionLevel.CENTRAL)
        result = await session.execute(stmt)
        central_depts = result.scalars().all()

        assert len(central_depts) == 2
        assert {d.code for d in central_depts} == {"PESO", "CGWA"}
