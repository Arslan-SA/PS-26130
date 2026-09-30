"""
Unit tests for Clearance Dependency & DAG Engine (Fragment 51).
Validates cycle detection, Kahn's topological sort, critical turnaround path calculation,
and real-time prerequisite unlock state evaluation.
"""

import pytest
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.approval_requirement import ApprovalRequirement, RequirementStatus
from app.services.dependency_engine import DependencyEngineService


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def test_detect_cycles_in_dag():
    """Verify cycle detection correctly identifies cycles and confirms valid DAGs."""
    valid_edges = [
        ("CTE_PCB", "CTO_PCB"),
        ("CTO_PCB", "FACTORY_LIC"),
        ("FIRE_NOC", "FACTORY_LIC"),
    ]
    assert DependencyEngineService.detect_cycles(valid_edges) is False

    cyclic_edges = [
        ("CTE_PCB", "CTO_PCB"),
        ("CTO_PCB", "FACTORY_LIC"),
        ("FACTORY_LIC", "CTE_PCB"),  # Cycle back to CTE!
    ]
    assert DependencyEngineService.detect_cycles(cyclic_edges) is True


def test_topological_sort_order():
    """Verify topological sort places all prerequisites before dependents."""
    nodes = ["FACTORY_LIC", "CTO_PCB", "FIRE_NOC", "CTE_PCB"]
    edges = [
        ("CTE_PCB", "CTO_PCB"),
        ("CTO_PCB", "FACTORY_LIC"),
        ("FIRE_NOC", "FACTORY_LIC"),
    ]
    order = DependencyEngineService.topological_sort(nodes, edges)

    # Prerequisite verification
    assert order.index("CTE_PCB") < order.index("CTO_PCB")
    assert order.index("CTO_PCB") < order.index("FACTORY_LIC")
    assert order.index("FIRE_NOC") < order.index("FACTORY_LIC")


def test_calculate_critical_path():
    """Verify critical path returns the longest sequence duration and nodes."""
    nodes = ["CTE_PCB", "CTO_PCB", "FIRE_NOC", "FACTORY_LIC"]
    edges = [
        ("CTE_PCB", "CTO_PCB"),
        ("CTO_PCB", "FACTORY_LIC"),
        ("FIRE_NOC", "FACTORY_LIC"),
    ]
    sla_map = {
        "CTE_PCB": 45,
        "CTO_PCB": 30,
        "FIRE_NOC": 21,
        "FACTORY_LIC": 30,
    }

    max_days, path = DependencyEngineService.calculate_critical_path(nodes, edges, sla_map)

    # Longest path: CTE_PCB (45) -> CTO_PCB (30) -> FACTORY_LIC (30) = 105 days
    assert max_days == 105
    assert path == ["CTE_PCB", "CTO_PCB", "FACTORY_LIC"]


@pytest.mark.asyncio
async def test_evaluate_requirement_unlocks():
    """Verify real-time prerequisite unlock logic against approval statuses."""
    async with AsyncSessionLocal() as session:
        req_cte = ApprovalRequirement(
            business_id="biz-001",
            approval_id="app-cte",
            status=RequirementStatus.NOT_STARTED,
            trigger_reason="Red category unit",
        )
        req_cto = ApprovalRequirement(
            business_id="biz-001",
            approval_id="app-cto",
            status=RequirementStatus.NOT_STARTED,
            trigger_reason="Red category unit",
        )
        req_fact = ApprovalRequirement(
            business_id="biz-001",
            approval_id="app-fact",
            status=RequirementStatus.NOT_STARTED,
            trigger_reason="150 workers",
        )

        code_map = {
            "app-cte": "CTE_PCB",
            "app-cto": "CTO_PCB",
            "app-fact": "FACTORY_LIC",
        }

        # 1. Initially CTE has 0 mandatory prereqs -> unlocked. CTO is locked by CTE.
        unlocks = await DependencyEngineService.evaluate_requirement_unlocks(
            session, [req_cte, req_cto, req_fact], code_map
        )

        assert unlocks["CTE_PCB"].is_unlocked is True
        assert unlocks["CTO_PCB"].is_unlocked is False
        assert "CTE_PCB" in unlocks["CTO_PCB"].missing_prerequisites
        assert unlocks["FACTORY_LIC"].is_unlocked is False

        # 2. When CTE is APPROVED -> CTO becomes unlocked
        req_cte.status = RequirementStatus.APPROVED
        unlocks_after = await DependencyEngineService.evaluate_requirement_unlocks(
            session, [req_cte, req_cto, req_fact], code_map
        )
        assert unlocks_after["CTO_PCB"].is_unlocked is True
        assert len(unlocks_after["CTO_PCB"].missing_prerequisites) == 0
