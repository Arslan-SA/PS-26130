"""
Integration test suite for Statutory Application Workflow REST APIs (Fragments 77, 78, 80, 81, 82, 83, 84, 85, 87, 88, 89).
Tests full API surface across Industry User, Department Officer, and Field Inspector roles.
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
async def api_fixtures():
    """Setup test users across all roles, department, clearance, and business."""
    async with AsyncSessionLocal() as session:
        promoter = User(
            email="promoter@udyamsetu.in",
            hashed_password="hashed_pw_123",
            full_name="Rajiv Singhal",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        officer = User(
            email="officer@spcb.gov.in",
            hashed_password="hashed_pw_123",
            full_name="Ananya Sen",
            role=UserRole.DEPARTMENT_OFFICER,
            department_id="SPCB",
            is_active=True,
            is_verified=True,
        )
        inspector = User(
            email="inspector@spcb.gov.in",
            hashed_password="hashed_pw_123",
            full_name="Vikas Pandey",
            role=UserRole.INSPECTOR,
            department_id="SPCB",
            is_active=True,
            is_verified=True,
        )
        rival = User(
            email="rival@other.in",
            hashed_password="hashed_pw_123",
            full_name="Competitor",
            role=UserRole.INDUSTRY_USER,
            is_active=True,
            is_verified=True,
        )
        session.add_all([promoter, officer, inspector, rival])
        await session.flush()

        dept = Department(
            code="SPCB",
            name="State Pollution Control Board",
            jurisdiction_level=JurisdictionLevel.STATE,
        )
        session.add(dept)

        approval = Approval(
            code="CTE_PCB",
            title="Consent to Establish (CTE)",
            department_code="SPCB",
            issuing_authority="State Pollution Control Board",
            sla_days=30,
            estimated_fee_base=20000.0,
        )
        session.add(approval)
        await session.flush()

        biz = Business(
            user_id=promoter.id,
            legal_name="Singhal Bio-Fertilizers Ltd",
            entity_type=EntityType.PUBLIC_LIMITED,
            msme_category=MSMECategory.MEDIUM,
            pan="SINGH1234Z",
        )
        session.add(biz)
        await session.flush()

        req = ApprovalRequirement(
            business_id=biz.id,
            approval_id=approval.id,
            status=RequirementStatus.NOT_STARTED,
            trigger_reason="Bio-fertilizer manufacturing plant discharge assessment.",
            estimated_fee=20000.0,
            sla_deadline_days=30,
        )
        session.add(req)
        await session.commit()

        token_promoter = create_access_token({"sub": str(promoter.id)})
        token_officer = create_access_token({"sub": str(officer.id)})
        token_inspector = create_access_token({"sub": str(inspector.id)})
        token_rival = create_access_token({"sub": str(rival.id)})

        return {
            "promoter": promoter,
            "officer": officer,
            "inspector": inspector,
            "rival": rival,
            "biz": biz,
            "approval": approval,
            "headers_promoter": {"Authorization": f"Bearer {token_promoter}"},
            "headers_officer": {"Authorization": f"Bearer {token_officer}"},
            "headers_inspector": {"Authorization": f"Bearer {token_inspector}"},
            "headers_rival": {"Authorization": f"Bearer {token_rival}"},
        }


@pytest.mark.asyncio
async def test_full_application_api_lifecycle(api_fixtures):
    """
    End-to-End API test covering:
    1. Create Draft Application (Industry)
    2. List Applications (Industry)
    3. Submit Application with Fee (Industry)
    4. Officer Inbox Summary & Department Queue (Officer)
    5. Officer Begins Review (Officer)
    6. Officer Raises Query (Officer)
    7. Applicant Responds to Query (Industry)
    8. Applicant Resubmits Application (Industry)
    9. Officer Schedules Inspection (Officer)
    10. Inspector Views Schedule & Submits Report (Inspector)
    11. Officer Grants Final Approval & Certificate (Officer)
    """
    fix = api_fixtures
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Create draft application
        create_resp = await client.post(
            "/api/v1/applications/",
            headers=fix["headers_promoter"],
            json={
                "business_id": fix["biz"].id,
                "approval_id": fix["approval"].id,
                "application_data": {"project_cost_cr": 25.0, "power_hp": 120},
                "attached_document_ids": ["doc-eia-report-01"],
            },
        )
        assert create_resp.status_code == 201
        app_data = create_resp.json()
        app_id = app_data["id"]
        assert app_data["status"] == "DRAFT"
        assert app_data["application_number"].startswith("APP-")

        # Step 2: List applications as promoter
        list_resp = await client.get("/api/v1/applications/", headers=fix["headers_promoter"])
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        # Competitor cannot see it
        rival_list = await client.get("/api/v1/applications/", headers=fix["headers_rival"])
        assert rival_list.status_code == 200
        assert len(rival_list.json()) == 0

        # Step 3: Submit application with fee receipt
        submit_resp = await client.post(
            f"/api/v1/applications/{app_id}/submit",
            headers=fix["headers_promoter"],
            json={
                "fee_paid": True,
                "fee_reference": "BHARATKOSH-2026-78901",
                "additional_remarks": "Submitted for statutory environmental clearance.",
            },
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == "SUBMITTED"
        assert submit_resp.json()["fee_reference"] == "BHARATKOSH-2026-78901"

        # Step 4: Officer checks inbox summary & queue
        inbox_resp = await client.get("/api/v1/officer/inbox-summary", headers=fix["headers_officer"])
        assert inbox_resp.status_code == 200
        inbox = inbox_resp.json()
        assert inbox["queue_metrics"]["pending_scrutiny"] == 1

        queue_resp = await client.get("/api/v1/officer/applications", headers=fix["headers_officer"])
        assert queue_resp.status_code == 200
        assert len(queue_resp.json()) == 1

        # Step 5: Officer begins scrutiny
        review_resp = await client.post(f"/api/v1/officer/applications/{app_id}/review", headers=fix["headers_officer"])
        assert review_resp.status_code == 200
        assert review_resp.json()["status"] == "UNDER_REVIEW"

        # Step 6: Officer raises query on document
        query_resp = await client.post(
            f"/api/v1/officer/applications/{app_id}/queries",
            headers=fix["headers_officer"],
            json={
                "query_title": "Solid waste disposal methodology",
                "query_text": "Clarify authorized TSDF hazardous waste disposal vendor agreement.",
            },
        )
        assert query_resp.status_code == 201
        query_data = query_resp.json()
        query_id = query_data["id"]
        assert query_data["status"] == "OPEN"

        # Step 7: Applicant responds to query
        resp_query = await client.post(
            f"/api/v1/applications/{app_id}/queries/{query_id}/respond",
            headers=fix["headers_promoter"],
            json={
                "response_text": "Agreement executed with Mumbai Waste Management Ltd (TSDF Taloja).",
                "response_document_id": "doc-tsdf-agreement-uuid",
            },
        )
        assert resp_query.status_code == 200
        assert resp_query.json()["status"] == "RESOLVED"

        # Step 8: Applicant resubmits application
        resubmit_resp = await client.post(
            f"/api/v1/applications/{app_id}/resubmit?remarks=TSDF+clarification+provided",
            headers=fix["headers_promoter"],
        )
        assert resubmit_resp.status_code == 200
        assert resubmit_resp.json()["status"] == "RESUBMITTED"

        # Step 9: Officer schedules site inspection
        sched_time = datetime.now(timezone.utc).isoformat()
        insp_resp = await client.post(
            f"/api/v1/officer/applications/{app_id}/schedule-inspection",
            headers=fix["headers_officer"],
            json={
                "inspector_id": fix["inspector"].id,
                "scheduled_date": sched_time,
                "instructions": "Inspect solid waste containment pit and ETP foundations.",
            },
        )
        assert insp_resp.status_code == 201
        insp_id = insp_resp.json()["id"]

        # Step 10: Inspector views schedule and submits inspection report
        inspector_sched = await client.get("/api/v1/inspector/schedule", headers=fix["headers_inspector"])
        assert inspector_sched.status_code == 200
        assert len(inspector_sched.json()) == 1

        report_resp = await client.post(
            f"/api/v1/inspector/inspections/{insp_id}/report",
            headers=fix["headers_inspector"],
            json={
                "findings": "Physical verification completed. TSDF containment dykes comply with CPCB guidelines.",
                "checklist_results": {"tsdf_bund_sealed": True, "green_belt_area_compliant": True},
                "recommendation": "SATISFACTORY",
                "geo_latitude": 19.1234,
                "geo_longitude": 73.0012,
            },
        )
        assert report_resp.status_code == 200
        assert report_resp.json()["status"] == "COMPLETED"

        # Step 11: Officer renders final Approval determination
        decision_resp = await client.post(
            f"/api/v1/officer/applications/{app_id}/determine",
            headers=fix["headers_officer"],
            json={
                "decision": "APPROVED",
                "remarks": "CTE granted for bio-fertilizer production under Water & Air Acts.",
                "validity_years": 5,
            },
        )
        assert decision_resp.status_code == 200
        final_app = decision_resp.json()
        assert final_app["status"] == "APPROVED"
        assert final_app["approval_certificate_number"].startswith("CERT-SPCB-")
        assert final_app["validity_years"] == 5
        assert len(final_app["status_history"]) >= 6
