"""
Unit tests for Approval statutory catalog domain model (Fragment 41).
Validates clearance attributes, constraints, default SLA/fee values, and string representations.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.approval import Approval


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_approval_creation_and_defaults():
    """Verify that an Approval catalog record can be persisted with default values."""
    async with AsyncSessionLocal() as session:
        approval = Approval(
            code="CTE_PCB",
            title="Consent to Establish (CTE) under Water and Air Acts",
            department_code="SPCB",
            issuing_authority="State Pollution Control Board",
            statutory_act="Water (Prevention & Control of Pollution) Act 1974",
            validity_period_months=60,
            is_mandatory=True,
            sla_days=45,
            estimated_fee_base=25000.0,
            description="Mandatory prior environmental clearance before industrial construction.",
        )
        session.add(approval)
        await session.commit()
        await session.refresh(approval)

        assert approval.id is not None
        assert approval.code == "CTE_PCB"
        assert approval.sla_days == 45
        assert approval.estimated_fee_base == 25000.0
        assert approval.is_mandatory is True
        assert "<Approval code='CTE_PCB'" in repr(approval)


@pytest.mark.asyncio
async def test_approval_unique_code_constraint():
    """Verify that clearance codes are strictly unique across the statutory catalog."""
    async with AsyncSessionLocal() as session:
        app1 = Approval(
            code="FIRE_NOC",
            title="Fire Safety Certificate",
            department_code="FIRE",
            issuing_authority="State Fire Services",
        )
        session.add(app1)
        await session.commit()

        app2 = Approval(
            code="FIRE_NOC",
            title="Duplicate Fire Clearance",
            department_code="FIRE",
            issuing_authority="State Fire Services",
        )
        session.add(app2)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_approval_query_by_department():
    """Verify filtering and querying approvals by issuing department code."""
    async with AsyncSessionLocal() as session:
        clearances = [
            Approval(code="CTE", title="CTE", department_code="SPCB", issuing_authority="SPCB"),
            Approval(code="CTO", title="CTO", department_code="SPCB", issuing_authority="SPCB"),
            Approval(code="FACTORY_LIC", title="Factory License", department_code="DISH", issuing_authority="DISH"),
        ]
        session.add_all(clearances)
        await session.commit()

        stmt = select(Approval).where(Approval.department_code == "SPCB")
        result = await session.execute(stmt)
        spcb_approvals = result.scalars().all()

        assert len(spcb_approvals) == 2
        assert {a.code for a in spcb_approvals} == {"CTE", "CTO"}
