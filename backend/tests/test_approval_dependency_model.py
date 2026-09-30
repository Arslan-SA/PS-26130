"""
Unit tests for ApprovalDependency domain model (Fragment 50).
Validates directed clearance DAG edges, constraint uniqueness, and prerequisite filtering.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.approval_dependency import ApprovalDependency, DependencyType


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_create_approval_dependency():
    """Verify that an ApprovalDependency edge can be stored with statutory metadata."""
    async with AsyncSessionLocal() as session:
        dep = ApprovalDependency(
            from_approval_code="CTE_PCB",
            to_approval_code="CTO_PCB",
            dependency_type=DependencyType.MANDATORY_PREREQUISITE,
            description="Consent to Establish is mandatory before trial runs or Consent to Operate.",
            enacted_statute="Water Act 1974 & Air Act 1981",
        )
        session.add(dep)
        await session.commit()
        await session.refresh(dep)

        assert dep.id is not None
        assert dep.from_approval_code == "CTE_PCB"
        assert dep.to_approval_code == "CTO_PCB"
        assert dep.dependency_type == DependencyType.MANDATORY_PREREQUISITE
        assert "<ApprovalDependency CTE_PCB -> CTO_PCB" in repr(dep)


@pytest.mark.asyncio
async def test_duplicate_dependency_edge_rejected():
    """Verify that duplicate directed dependency edges trigger IntegrityError."""
    async with AsyncSessionLocal() as session:
        dep1 = ApprovalDependency(
            from_approval_code="FIRE_NOC",
            to_approval_code="FACTORY_LIC",
            dependency_type=DependencyType.MANDATORY_PREREQUISITE,
        )
        session.add(dep1)
        await session.commit()

        dep2 = ApprovalDependency(
            from_approval_code="FIRE_NOC",
            to_approval_code="FACTORY_LIC",
            dependency_type=DependencyType.RECOMMENDED_PARALLEL,
        )
        session.add(dep2)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_query_incoming_prerequisites():
    """Verify querying all clearances that must precede Factory License."""
    async with AsyncSessionLocal() as session:
        edges = [
            ApprovalDependency(from_approval_code="CTE_PCB", to_approval_code="CTO_PCB"),
            ApprovalDependency(from_approval_code="FIRE_NOC", to_approval_code="FACTORY_LIC"),
            ApprovalDependency(from_approval_code="CTO_PCB", to_approval_code="FACTORY_LIC"),
            ApprovalDependency(from_approval_code="POWER_HT", to_approval_code="FACTORY_LIC"),
        ]
        session.add_all(edges)
        await session.commit()

        # Query prerequisites of FACTORY_LIC
        stmt = select(ApprovalDependency).where(ApprovalDependency.to_approval_code == "FACTORY_LIC")
        result = await session.execute(stmt)
        prereqs = result.scalars().all()

        assert len(prereqs) == 3
        prereq_codes = {p.from_approval_code for p in prereqs}
        assert prereq_codes == {"FIRE_NOC", "CTO_PCB", "POWER_HT"}
