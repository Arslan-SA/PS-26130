"""
End-to-End Approval Engine Workflow Integration Test (Fragment 57).
Validates the complete statutory clearance lifecycle:
- Automated discovery and statutory fee / SLA calculation
- Prerequisite DAG topological sequencing and critical path identification
- Personalized milestone Gantt roadmap forward-pass scheduling
- Real-time Next-Action priority queues and bottleneck unblocking
- Immutable audit history tracking and reference number persistence
- Statutory document checklist retrieval
- Strict multi-tenant RBAC isolation across industry users
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
async def workflow_environment():
    """Sets up primary enterprise and a separate unprivileged competitor."""
    async with AsyncSessionLocal() as session:
        # 1. Primary enterprise owner
        promoter = User(
            email="promoter@bharatsemicon.in",
            hashed_password="SecurePassword123!",
            full_name="Dr. Harish Chandra",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        session.add(promoter)

        # 2. Competitor / unauthorized user
        competitor = User(
            email="promoter@rivalcorp.in",
            hashed_password="SecurePassword123!",
            full_name="Devendra Rival",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        session.add(competitor)
        await session.commit()
        await session.refresh(promoter)
        await session.refresh(competitor)

        # Primary Business
        biz = Business(
            user_id=promoter.id,
            legal_name="Bharat Semiconductor Fabrication Ltd",
            trade_name="Bharat SemiFab",
            entity_type=EntityType.PUBLIC_LIMITED,
            msme_category=MSMECategory.LARGE,
            pan="AAACB7777K",
            gstin="27AAACB7777K1Z8",
        )
        session.add(biz)
        await session.commit()
        await session.refresh(biz)

        # Profile triggering Red pollution, large water/power, and factories act
        profile = BusinessProfile(
            business_id=biz.id,
            manufacturing_activity="Semiconductor wafer etching and chemical vapor deposition",
            industry_scale=IndustryScale.LARGE_SCALE,
            pollution_category=PollutionCategory.RED,
            land_area_sqm=20000.0,
            total_employees=450,
            plant_machinery_investment=850000000.0,
            power_requirement_kw=2500.0,
            water_requirement_kld=180.0,
        )
        session.add(profile)
        await session.commit()

        token_promoter = create_access_token({"sub": promoter.id, "role": promoter.role.value})
        token_competitor = create_access_token({"sub": competitor.id, "role": competitor.role.value})

        return {
            "business_id": biz.id,
            "promoter_headers": {"Authorization": f"Bearer {token_promoter}"},
            "competitor_headers": {"Authorization": f"Bearer {token_competitor}"},
        }


@pytest.mark.asyncio
async def test_e2e_full_clearance_lifecycle(workflow_environment):
    """
    Simulate the full end-to-end statutory approval journey:
    Discovery -> Graph -> Roadmap -> Next Actions -> Checklist -> Filing -> Approval -> Unblocking.
    """
    biz_id = workflow_environment["business_id"]
    headers = workflow_environment["promoter_headers"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Step 1: Regulatory Discovery
        disc_resp = await client.post(f"/api/v1/approvals/discover/{biz_id}", headers=headers)
        assert disc_resp.status_code == 200
        disc_data = disc_resp.json()
        assert disc_data["count"] >= 5
        assert disc_data["summary"]["total_estimated_fee"] > 0
        assert disc_data["summary"]["pre_establishment_critical_days"] > 0

        req_map = {r["approval"]["code"]: r for r in disc_data["requirements"]}
        assert "CTE_PCB" in req_map
        assert "CTO_PCB" in req_map
        assert "FACTORY_LIC" in req_map
        assert "POWER_HT" in req_map
        cte_id = req_map["CTE_PCB"]["id"]
        cto_id = req_map["CTO_PCB"]["id"]

        # 2. Step 2: Clearance Dependency DAG
        graph_resp = await client.get(f"/api/v1/approvals/graph/{biz_id}", headers=headers)
        assert graph_resp.status_code == 200
        graph_data = graph_resp.json()
        assert len(graph_data["nodes"]) >= 5
        assert len(graph_data["edges"]) >= 3
        assert "CTE_PCB" in graph_data["topological_order"]
        # CTE must precede CTO in topological ordering
        cte_idx = graph_data["topological_order"].index("CTE_PCB")
        cto_idx = graph_data["topological_order"].index("CTO_PCB")
        assert cte_idx < cto_idx

        # 3. Step 3: Personalized Clearance Roadmap (Gantt Schedule)
        roadmap_resp = await client.get(f"/api/v1/approvals/roadmap/{biz_id}", headers=headers)
        assert roadmap_resp.status_code == 200
        roadmap_data = roadmap_resp.json()
        assert roadmap_data["total_calendar_days"] >= 45
        assert len(roadmap_data["milestones"]) >= 2
        assert len(roadmap_data["activities"]) >= 5

        # 4. Step 4: Next-Action Dynamic Recommendation Queue
        actions_resp = await client.get(f"/api/v1/approvals/next-actions/{biz_id}", headers=headers)
        assert actions_resp.status_code == 200
        actions_data = actions_resp.json()
        top_action = actions_data["top_immediate_action"]
        assert top_action is not None
        assert top_action["approval_code"] == "CTE_PCB"
        assert top_action["action_type"] == "APPLY_NOW"
        assert top_action["priority"] == "CRITICAL"

        action_dict = {a["approval_code"]: a for a in actions_data["actions"]}
        # CTO must initially be blocked by CTE
        assert action_dict["CTO_PCB"]["action_type"] == "RESOLVE_PREREQUISITES"
        assert "CTE_PCB" in action_dict["CTO_PCB"]["blocked_by"]

        # 5. Step 5: Fetch Checklist for CTE_PCB
        chk_resp = await client.get("/api/v1/approvals/CTE_PCB/checklist", headers=headers)
        assert chk_resp.status_code == 200
        chk_data = chk_resp.json()
        assert chk_data["approval_code"] == "CTE_PCB"
        assert len(chk_data["items"]) >= 3

        # 6. Step 6: Industrialist files CTE application (Transition to SUBMITTED)
        submit_payload = {
            "status": "SUBMITTED",
            "remarks": "Form XIII and Environmental Management Plan uploaded.",
            "reference_number": "PCB-SUB-2026-00451",
            "notes": "Fast-track scrutiny requested.",
        }
        patch_resp = await client.patch(
            f"/api/v1/approvals/requirements/{cte_id}/status",
            json=submit_payload,
            headers=headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "SUBMITTED"

        # 7. Step 7: Officer approves CTE (Transition to APPROVED)
        approve_payload = {
            "status": "APPROVED",
            "remarks": "Technical committee recommended grant. Consent valid for 5 years.",
            "reference_number": "PCB-CTE-GRANT-2026-9901",
        }
        approve_resp = await client.patch(
            f"/api/v1/approvals/requirements/{cte_id}/status",
            json=approve_payload,
            headers=headers,
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "APPROVED"

        # 8. Step 8: Verify DAG unblocking in Next-Actions Queue
        actions_after = (await client.get(f"/api/v1/approvals/next-actions/{biz_id}", headers=headers)).json()
        action_dict_after = {a["approval_code"]: a for a in actions_after["actions"]}

        # CTE_PCB is now DOWNLOAD_CERTIFICATE
        assert action_dict_after["CTE_PCB"]["action_type"] == "DOWNLOAD_CERTIFICATE"

        # CTO_PCB and POWER_HT are now UNBLOCKED!
        assert action_dict_after["CTO_PCB"]["is_unlocked"] is True
        assert action_dict_after["CTO_PCB"]["action_type"] == "APPLY_NOW"
        assert action_dict_after["POWER_HT"]["is_unlocked"] is True

        # 9. Step 9: Audit Trail History
        cte_hist = (await client.get(f"/api/v1/approvals/requirements/{cte_id}/history", headers=headers)).json()
        assert len(cte_hist) == 2
        assert cte_hist[0]["to_status"] == "APPROVED"
        assert cte_hist[0]["reference_number"] == "PCB-CTE-GRANT-2026-9901"
        assert cte_hist[1]["to_status"] == "SUBMITTED"
        assert cte_hist[1]["reference_number"] == "PCB-SUB-2026-00451"

        biz_hist = (await client.get(f"/api/v1/approvals/history/{biz_id}", headers=headers)).json()
        assert len(biz_hist) >= 2


@pytest.mark.asyncio
async def test_e2e_approval_security_access_control(workflow_environment):
    """Verify competitor user cannot view or alter another enterprise's statutory clearances."""
    biz_id = workflow_environment["business_id"]
    unauthorized_headers = workflow_environment["competitor_headers"]
    authorized_headers = workflow_environment["promoter_headers"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Seed requirements first
        await client.post(f"/api/v1/approvals/discover/{biz_id}", headers=authorized_headers)

        # Unauthorized access attempts
        endpoints = [
            ("GET", f"/api/v1/approvals/business/{biz_id}"),
            ("GET", f"/api/v1/approvals/summary/{biz_id}"),
            ("GET", f"/api/v1/approvals/graph/{biz_id}"),
            ("GET", f"/api/v1/approvals/roadmap/{biz_id}"),
            ("GET", f"/api/v1/approvals/next-actions/{biz_id}"),
            ("GET", f"/api/v1/approvals/history/{biz_id}"),
        ]

        for method, endpoint in endpoints:
            resp = await client.request(method, endpoint, headers=unauthorized_headers)
            assert resp.status_code == 403, f"Expected 403 on {endpoint}, got {resp.status_code}"
