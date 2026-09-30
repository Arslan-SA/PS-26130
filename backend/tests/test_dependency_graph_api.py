"""
Integration test suite for Statutory Clearance Dependency Graph REST API (Fragment 52).
Validates DAG node generation, edge connectivity, real-time unlock status, and critical path response.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import create_access_token
from app.main import app
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
async def graph_test_fixtures():
    """Create owner user, business, and profile."""
    async with AsyncSessionLocal() as session:
        user = User(
            email="promoter@zenithsteel.in",
            hashed_password="SecurePassword123!",
            full_name="Zenith Promoter",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        business = Business(
            user_id=user.id,
            legal_name="Zenith Heavy Engineering Limited",
            trade_name="Zenith Heavy",
            entity_type=EntityType.PUBLIC_LIMITED,
            msme_category=MSMECategory.LARGE,
            pan="AAACZ9999L",
            gstin="27AAACZ9999L1Z8",
        )
        session.add(business)
        await session.commit()
        await session.refresh(business)

        profile = BusinessProfile(
            business_id=business.id,
            manufacturing_activity="Heavy machinery fabrication, casting, and metal coating",
            industry_scale=IndustryScale.LARGE_SCALE,
            pollution_category=PollutionCategory.RED,
            land_area_sqm=7500.0,
            total_employees=160,
            plant_machinery_investment=180000000.0,
            power_requirement_kw=550.0,
            water_requirement_kld=40.0,
        )
        session.add(profile)
        await session.commit()

        token = create_access_token({"sub": user.id, "role": user.role.value})
        return {"business_id": business.id, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.mark.asyncio
async def test_get_approval_dependency_graph(graph_test_fixtures):
    """Verify GET /api/v1/approvals/graph/{business_id} returns nodes, edges, and critical path."""
    biz_id = graph_test_fixtures["business_id"]
    headers = graph_test_fixtures["headers"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/approvals/graph/{biz_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["business_id"] == biz_id
        assert len(data["nodes"]) >= 5
        assert len(data["edges"]) >= 3
        assert len(data["topological_order"]) >= 5
        assert len(data["critical_path"]) >= 2
        assert data["critical_path_days"] >= 45

        # Verify node properties
        node_map = {n["id"]: n for n in data["nodes"]}
        assert "CTE_PCB" in node_map
        assert "CTO_PCB" in node_map
        assert node_map["CTE_PCB"]["is_unlocked"] is True
        assert node_map["CTO_PCB"]["is_unlocked"] is False
        assert "CTE_PCB" in node_map["CTO_PCB"]["missing_prerequisites"]

        # Verify edge properties
        edge_ids = {e["id"] for e in data["edges"]}
        assert "CTE_PCB->CTO_PCB" in edge_ids
