"""
End-to-End Test Suite for Multi-Department Approvals Workflow Engine (Fragment 90).
Comprehensive integration tests covering complete lifecycles across Industry Promoters,
Department Scrutiny Officers, and Field Inspectors.
"""

from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import create_access_token
from app.main import app
from app.models.approval import Approval
from app.models.approval_requirement import ApprovalRequirement, RequirementStatus
from app.models.business import Business, EntityType, MSMECategory
from app.models.department import Department, JurisdictionLevel
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def e2e_env():
    """Seed comprehensive regulatory environment with multiple departments, users, and clearances."""
    async with AsyncSessionLocal() as session:
        # 1. Users
        promoter1 = User(
            email="founder@greenenergy.in",
            hashed_password="hashed_pw_xyz",
            full_name="Vikram Sethi",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        promoter2 = User(
            email="competitor@rival.in",
            hashed_password="hashed_pw_xyz",
            full_name="Rival Promoter",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        officer_spcb = User(
            email="officer@spcb.gov.in",
            hashed_password="hashed_pw_xyz",
            full_name="Officer Rao",
            role=UserRole.DEPARTMENT_OFFICER,
            department_id="SPCB",
            is_active=True,
            is_verified=True,
        )
        officer_fire = User(
            email="officer@fire.gov.in",
            hashed_password="hashed_pw_xyz",
            full_name="Fire Chief Deshpande",
            role=UserRole.DEPARTMENT_OFFICER,
            department_id="FIRE",
            is_active=True,
            is_verified=True,
        )
        inspector_spcb = User(
            email="inspector@spcb.gov.in",
            hashed_password="hashed_pw_xyz",
            full_name="Inspector Kulkarni",
            role=UserRole.INSPECTOR,
            department_id="SPCB",
            is_active=True,
            is_verified=True,
        )
        session.add_all([promoter1, promoter2, officer_spcb, officer_fire, inspector_spcb])
        await session.flush()

        # 2. Departments
        dept_spcb = Department(
            code="SPCB",
            name="State Pollution Control Board",
            jurisdiction_level=JurisdictionLevel.STATE,
        )
        dept_fire = Department(
            code="FIRE",
            name="State Fire and Emergency Services",
            jurisdiction_level=JurisdictionLevel.STATE,
        )
        session.add_all([dept_spcb, dept_fire])

        # 3. Clearances
        cte_approval = Approval(
            code="CTE_PCB",
            title="Consent to Establish (CTE)",
            department_code="SPCB",
            issuing_authority="SPCB",
            sla_days=30,
            estimated_fee_base=25000.0,
        )
        fire_approval = Approval(
            code="FIRE_NOC",
            title="Provisional Fire Safety NOC",
            department_code="FIRE",
            issuing_authority="Fire Services",
            sla_days=21,
            estimated_fee_base=12000.0,
        )
        session.add_all([cte_approval, fire_approval])
        await session.flush()

        # 4. Businesses
        biz1 = Business(
            user_id=promoter1.id,
            legal_name="Green Energy Biofuels Ltd",
            entity_type=EntityType.PUBLIC_LIMITED,
            msme_category=MSMECategory.MEDIUM,
            pan="GREEN1234A",
        )
        biz2 = Business(
            user_id=promoter2.id,
            legal_name="Rival Fuels Pvt Ltd",
            entity_type=EntityType.PRIVATE_LIMITED,
            msme_category=MSMECategory.SMALL,
            pan="RIVAL1234B",
        )
        session.add_all([biz1, biz2])
        await session.flush()

        # 5. Requirement
        req1 = ApprovalRequirement(
            business_id=biz1.id,
            approval_id=cte_approval.id,
            status=RequirementStatus.NOT_STARTED,
            trigger_reason="Chemical processing plant produces industrial effluent.",
            estimated_fee=25000.0,
            sla_deadline_days=30,
        )
        session.add(req1)
        await session.commit()

        # Auth tokens
        t_promoter1 = create_access_token({"sub": str(promoter1.id)})
        t_promoter2 = create_access_token({"sub": str(promoter2.id)})
        t_spcb = create_access_token({"sub": str(officer_spcb.id)})
        t_fire = create_access_token({"sub": str(officer_fire.id)})
        t_inspector = create_access_token({"sub": str(inspector_spcb.id)})

        return {
            "biz1": biz1,
            "biz2": biz2,
            "cte": cte_approval,
            "fire": fire_approval,
            "req1": req1,
            "inspector_spcb": inspector_spcb,
            "headers_p1": {"Authorization": f"Bearer {t_promoter1}"},
            "headers_p2": {"Authorization": f"Bearer {t_promoter2}"},
            "headers_spcb": {"Authorization": f"Bearer {t_spcb}"},
            "headers_fire": {"Authorization": f"Bearer {t_fire}"},
            "headers_insp": {"Authorization": f"Bearer {t_inspector}"},
        }


@pytest.mark.asyncio
async def test_e2e_complete_approval_flow_with_inspection(e2e_env):
    """
    E2E Scenario 1: Complete statutory clearance lifecycle from Draft to Grant with site inspection.
    """
    env = e2e_env
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Promoter creates draft application
        create_res = await client.post(
            "/api/v1/applications/",
            headers=env["headers_p1"],
            json={
                "business_id": env["biz1"].id,
                "approval_id": env["cte"].id,
                "application_data": {"water_demand_kld": 75, "effluent_generation_kld": 60},
                "attached_document_ids": ["doc-dpr-1", "doc-site-plan-2"],
                "fee_amount": 25000.0,
            },
        )
        assert create_res.status_code == 201
        app_id = create_res.json()["id"]
        assert create_res.json()["status"] == "DRAFT"

        # 2. Promoter submits application
        submit_res = await client.post(
            f"/api/v1/applications/{app_id}/submit",
            headers=env["headers_p1"],
            json={"fee_paid": True, "fee_reference": "CHALLAN-SPCB-2026-001"},
        )
        assert submit_res.status_code == 200
        assert submit_res.json()["status"] == "SUBMITTED"
        assert submit_res.json()["sla_due_date"] is not None

        # 3. Officer initiates review
        review_res = await client.post(
            f"/api/v1/officer/applications/{app_id}/review",
            headers=env["headers_spcb"],
        )
        assert review_res.status_code == 200
        assert review_res.json()["status"] == "UNDER_REVIEW"

        # 4. Officer schedules site inspection
        sched_res = await client.post(
            f"/api/v1/officer/applications/{app_id}/schedule-inspection",
            headers=env["headers_spcb"],
            json={
                "inspector_id": env["inspector_spcb"].id,
                "scheduled_date": datetime.now(timezone.utc).isoformat(),
                "instructions": "Inspect ETP location and zero liquid discharge setup.",
            },
        )
        assert sched_res.status_code == 201
        insp_id = sched_res.json()["id"]

        # 5. Inspector verifies and submits report
        report_res = await client.post(
            f"/api/v1/inspector/inspections/{insp_id}/report",
            headers=env["headers_insp"],
            json={
                "findings": "Zero Liquid Discharge plant area demarcated. Ground water monitoring well established.",
                "checklist_results": {"etp_plan_verified": True, "zld_demarcated": True},
                "recommendation": "SATISFACTORY",
                "geo_latitude": 18.9876,
                "geo_longitude": 72.8234,
            },
        )
        assert report_res.status_code == 200
        assert report_res.json()["status"] == "COMPLETED"

        # 6. Officer issues final approval grant
        determine_res = await client.post(
            f"/api/v1/officer/applications/{app_id}/determine",
            headers=env["headers_spcb"],
            json={
                "decision": "APPROVED",
                "remarks": "CTE clearance granted under Water Act 1974 with ZLD conditions.",
                "validity_years": 5,
            },
        )
        assert determine_res.status_code == 200
        final_doc = determine_res.json()
        assert final_doc["status"] == "APPROVED"
        assert final_doc["approval_certificate_number"].startswith("CERT-SPCB-")
        assert final_doc["validity_years"] == 5
        assert len(final_doc["status_history"]) >= 5


@pytest.mark.asyncio
async def test_e2e_deficiency_query_and_resubmission_loop(e2e_env):
    """
    E2E Scenario 2: Officer raises deficiency query, applicant rectifies, and resubmits for grant.
    """
    env = e2e_env
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create and submit
        create_res = await client.post(
            "/api/v1/applications/",
            headers=env["headers_p1"],
            json={"business_id": env["biz1"].id, "approval_id": env["cte"].id},
        )
        app_id = create_res.json()["id"]
        await client.post(
            f"/api/v1/applications/{app_id}/submit",
            headers=env["headers_p1"],
            json={"fee_paid": True, "fee_reference": "CHALLAN-SPCB-002"},
        )
        await client.post(f"/api/v1/officer/applications/{app_id}/review", headers=env["headers_spcb"])

        # Officer raises query
        query_res = await client.post(
            f"/api/v1/officer/applications/{app_id}/queries",
            headers=env["headers_spcb"],
            json={
                "query_title": "Missing Acoustic Enclosure Specs",
                "query_text": "Provide decibel ratings and acoustic enclosure specs for 500 kVA DG set.",
            },
        )
        assert query_res.status_code == 201
        q_id = query_res.json()["id"]

        # Application is in QUERY_RAISED
        detail_res = await client.get(f"/api/v1/applications/{app_id}", headers=env["headers_p1"])
        assert detail_res.json()["status"] == "QUERY_RAISED"

        # Applicant responds
        resp_res = await client.post(
            f"/api/v1/applications/{app_id}/queries/{q_id}/respond",
            headers=env["headers_p1"],
            json={
                "response_text": "DG set acoustic enclosure certified by ARAI under CPCB noise standards.",
                "response_document_id": "doc-arai-certificate-uuid",
            },
        )
        assert resp_res.status_code == 200
        assert resp_res.json()["status"] == "RESOLVED"

        # Applicant resubmits
        resubmit_res = await client.post(
            f"/api/v1/applications/{app_id}/resubmit",
            headers=env["headers_p1"],
        )
        assert resubmit_res.status_code == 200
        assert resubmit_res.json()["status"] == "RESUBMITTED"


@pytest.mark.asyncio
async def test_e2e_rejection_scenario(e2e_env):
    """
    E2E Scenario 3: Statutory rejection with mandatory legal reasoning.
    """
    env = e2e_env
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post(
            "/api/v1/applications/",
            headers=env["headers_p1"],
            json={"business_id": env["biz1"].id, "approval_id": env["cte"].id},
        )
        app_id = create_res.json()["id"]
        await client.post(
            f"/api/v1/applications/{app_id}/submit",
            headers=env["headers_p1"],
            json={"fee_paid": True, "fee_reference": "CHALLAN-SPCB-003"},
        )
        await client.post(f"/api/v1/officer/applications/{app_id}/review", headers=env["headers_spcb"])

        # Rejection
        reject_res = await client.post(
            f"/api/v1/officer/applications/{app_id}/determine",
            headers=env["headers_spcb"],
            json={
                "decision": "REJECTED",
                "rejection_reason": "Proposed discharge into notified eco-sensitive zone violates SPCB siting criteria.",
            },
        )
        assert reject_res.status_code == 200
        assert reject_res.json()["status"] == "REJECTED"
        assert "eco-sensitive zone" in reject_res.json()["rejection_reason"]


@pytest.mark.asyncio
async def test_e2e_multi_department_isolation_and_security(e2e_env):
    """
    E2E Scenario 4: Cross-department isolation and multi-tenant security verification.
    """
    env = e2e_env
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post(
            "/api/v1/applications/",
            headers=env["headers_p1"],
            json={"business_id": env["biz1"].id, "approval_id": env["cte"].id},
        )
        app_id = create_res.json()["id"]

        # Competitor cannot view or submit
        steal_res = await client.get(f"/api/v1/applications/{app_id}", headers=env["headers_p2"])
        assert steal_res.status_code == 403

        # Submit as owner
        await client.post(
            f"/api/v1/applications/{app_id}/submit",
            headers=env["headers_p1"],
            json={"fee_paid": True, "fee_reference": "CHALLAN-004"},
        )

        # Fire officer cannot review SPCB clearance
        fire_res = await client.post(f"/api/v1/officer/applications/{app_id}/review", headers=env["headers_fire"])
        assert fire_res.status_code == 403
