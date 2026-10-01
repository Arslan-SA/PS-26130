"""
Comprehensive unit and service tests for Application Workflow Engine (Fragments 77, 78, 82, 83, 84, 85, 87, 88, 89).
"""

from datetime import datetime, timezone
import pytest
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.exceptions import (
    AuthorizationError,
    BusinessRuleViolationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.application import Application, ApplicationStatus
from app.models.application_query import QueryStatus
from app.models.approval import Approval
from app.models.approval_requirement import ApprovalRequirement, RequirementStatus
from app.models.business import Business, EntityType, MSMECategory
from app.models.department import Department, JurisdictionLevel
from app.models.inspection import InspectionRecommendation, InspectionStatus
from app.models.user import User, UserRole
from app.schemas.application import (
    ApplicationCreate,
    ApplicationQueryCreate,
    ApplicationQueryRespondPayload,
    ApplicationSubmitPayload,
    InspectionReportPayload,
    InspectionSchedulePayload,
    StatutoryDeterminationPayload,
)
from app.services.application_service import ApplicationWorkflowService


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _create_test_fixtures(session):
    """Seed base industry user, officer, inspector, department, approval, and business."""
    user = User(
        email="promoter@pharma.com",
        hashed_password="pw",
        full_name="Sunil Mehta",
        role=UserRole.INDUSTRY_USER,
    )
    officer = User(
        email="officer@spcb.gov.in",
        hashed_password="pw",
        full_name="Kavita Rao",
        role=UserRole.DEPARTMENT_OFFICER,
        department_id="SPCB",
    )
    inspector = User(
        email="inspector@spcb.gov.in",
        hashed_password="pw",
        full_name="Arun Joshi",
        role=UserRole.INSPECTOR,
        department_id="SPCB",
    )
    session.add_all([user, officer, inspector])
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
        estimated_fee_base=15000.0,
    )
    session.add(approval)
    await session.flush()

    biz = Business(
        user_id=user.id,
        legal_name="Mehta Formulations LLP",
        entity_type=EntityType.LLP,
        msme_category=MSMECategory.SMALL,
        pan="MEHTA1234K",
    )
    session.add(biz)
    await session.flush()

    req = ApprovalRequirement(
        business_id=biz.id,
        approval_id=approval.id,
        status=RequirementStatus.NOT_STARTED,
        trigger_reason="Chemical processing plant produces industrial effluents.",
        estimated_fee=15000.0,
        sla_deadline_days=30,
    )
    session.add(req)
    await session.commit()

    return user, officer, inspector, dept, approval, biz, req


@pytest.mark.asyncio
async def test_create_application_draft_and_history():
    """Fragment 77: Test draft application creation with audit tracking."""
    async with AsyncSessionLocal() as session:
        user, officer, inspector, dept, approval, biz, req = await _create_test_fixtures(session)

        payload = ApplicationCreate(
            business_id=biz.id,
            approval_id=approval.id,
            application_data={"plant_area_sqm": 2500, "investment_lakhs": 450},
            attached_document_ids=["doc-abc-123"],
            fee_amount=15000.0,
            fee_paid=False,
        )

        app = await ApplicationWorkflowService.create_application(session, payload, user)
        assert app.id is not None
        assert app.status == ApplicationStatus.DRAFT
        assert app.application_number.startswith("APP-")
        assert app.requirement_id == req.id
        assert app.department_code == "SPCB"
        assert len(app.status_history) == 1
        assert app.status_history[0].action == "CREATE_DRAFT"


@pytest.mark.asyncio
async def test_prevent_duplicate_active_application():
    """Fragment 77: Ensure cannot create duplicate active applications for same clearance."""
    async with AsyncSessionLocal() as session:
        user, officer, inspector, dept, approval, biz, req = await _create_test_fixtures(session)

        payload = ApplicationCreate(
            business_id=biz.id,
            approval_id=approval.id,
        )
        await ApplicationWorkflowService.create_application(session, payload, user)

        with pytest.raises(ConflictError) as exc_info:
            await ApplicationWorkflowService.create_application(session, payload, user)
        assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_submit_application_requires_fee_and_updates_requirement():
    """Fragment 78: Submitting draft validates payment and advances status and requirement."""
    async with AsyncSessionLocal() as session:
        user, officer, inspector, dept, approval, biz, req = await _create_test_fixtures(session)

        app = await ApplicationWorkflowService.create_application(
            session, ApplicationCreate(business_id=biz.id, approval_id=approval.id), user
        )

        # Missing fee reference raises error
        with pytest.raises(ValidationError):
            await ApplicationWorkflowService.submit_application(
                session, app.id, ApplicationSubmitPayload(fee_paid=False, fee_reference=""), user
            )

        # Successful submission
        submit_payload = ApplicationSubmitPayload(
            fee_paid=True,
            fee_reference="CHALLAN-2026-9999",
            additional_remarks="All environmental compliance documents attached.",
        )
        submitted_app = await ApplicationWorkflowService.submit_application(
            session, app.id, submit_payload, user
        )

        assert submitted_app.status == ApplicationStatus.SUBMITTED
        assert submitted_app.fee_paid is True
        assert submitted_app.fee_reference == "CHALLAN-2026-9999"
        assert submitted_app.submitted_at is not None
        assert submitted_app.sla_due_date is not None
        assert len(submitted_app.status_history) == 2
        assert submitted_app.status_history[0].action == "SUBMIT"

        # Verify linked requirement is also updated
        await session.refresh(req)
        assert req.status == RequirementStatus.SUBMITTED


@pytest.mark.asyncio
async def test_officer_review_and_deficiency_query_lifecycle():
    """Fragments 82, 83, 84, 85: Review commencement, query issuance, resolution, and resubmission."""
    async with AsyncSessionLocal() as session:
        user, officer, inspector, dept, approval, biz, req = await _create_test_fixtures(session)

        # 1. Create and submit
        app = await ApplicationWorkflowService.create_application(
            session, ApplicationCreate(business_id=biz.id, approval_id=approval.id), user
        )
        await ApplicationWorkflowService.submit_application(
            session, app.id, ApplicationSubmitPayload(fee_paid=True, fee_reference="REC-001"), user
        )

        # 2. Officer commences scrutiny
        under_review_app = await ApplicationWorkflowService.start_review(session, app.id, officer)
        assert under_review_app.status == ApplicationStatus.UNDER_REVIEW
        assert under_review_app.assigned_officer_id == officer.id

        await session.refresh(req)
        assert req.status == RequirementStatus.UNDER_REVIEW

        # 3. Officer raises deficiency query
        query_payload = ApplicationQueryCreate(
            query_title="Clarify Effluent Flow Rate",
            query_text="Please submit hourly peak discharge calculations for the ETP secondary clarifier.",
        )
        query = await ApplicationWorkflowService.raise_deficiency_query(
            session, app.id, query_payload, officer
        )
        assert query.status == QueryStatus.OPEN
        assert query.query_title == "Clarify Effluent Flow Rate"

        await session.refresh(app)
        assert app.status == ApplicationStatus.QUERY_RAISED

        # 4. Cannot resubmit while query is open
        with pytest.raises(BusinessRuleViolationError) as exc_info:
            await ApplicationWorkflowService.resubmit_application(session, app.id, None, user)
        assert "unresolved queries" in str(exc_info.value)

        # 5. Applicant responds to query with explanation and replacement doc
        resp_payload = ApplicationQueryRespondPayload(
            response_text="Peak discharge is 12 m3/hr. Revised engineering calculations attached.",
            response_document_id="doc-revised-etp-calc",
        )
        resolved_query = await ApplicationWorkflowService.respond_to_query(
            session, app.id, query.id, resp_payload, user
        )
        assert resolved_query.status == QueryStatus.RESOLVED
        assert resolved_query.resolved_at is not None

        # 6. Applicant resubmits application
        resubmitted_app = await ApplicationWorkflowService.resubmit_application(
            session, app.id, "Addressed ETP peak discharge clarification", user
        )
        assert resubmitted_app.status == ApplicationStatus.RESUBMITTED
        assert "doc-revised-etp-calc" in resubmitted_app.attached_document_ids


@pytest.mark.asyncio
async def test_inspection_scheduling_and_reporting():
    """Fragments 87, 88: Scheduling physical inspection and submitting findings with recommendation."""
    async with AsyncSessionLocal() as session:
        user, officer, inspector, dept, approval, biz, req = await _create_test_fixtures(session)

        app = await ApplicationWorkflowService.create_application(
            session, ApplicationCreate(business_id=biz.id, approval_id=approval.id), user
        )
        await ApplicationWorkflowService.submit_application(
            session, app.id, ApplicationSubmitPayload(fee_paid=True, fee_reference="REC-002"), user
        )
        await ApplicationWorkflowService.start_review(session, app.id, officer)

        # Schedule inspection
        sched_time = datetime.now(timezone.utc)
        insp_payload = InspectionSchedulePayload(
            inspector_id=inspector.id,
            scheduled_date=sched_time,
            instructions="Inspect hazardous waste shed and rainwater harvesting percolation pit.",
        )
        inspection = await ApplicationWorkflowService.schedule_inspection(
            session, app.id, insp_payload, officer
        )
        assert inspection.status == InspectionStatus.SCHEDULED
        assert inspection.inspector_id == inspector.id

        await session.refresh(app)
        assert app.status == ApplicationStatus.INSPECTION_SCHEDULED

        # Inspector submits report
        report_payload = InspectionReportPayload(
            findings="All containment dykes intact. Dedicated Hazardous waste shed verified.",
            checklist_results={"waste_shed_compliant": True, "fire_extinguishers": True},
            recommendation=InspectionRecommendation.SATISFACTORY,
            geo_latitude=19.0760,
            geo_longitude=72.8777,
        )
        completed_insp = await ApplicationWorkflowService.submit_inspection_report(
            session, inspection.id, report_payload, inspector
        )
        assert completed_insp.status == InspectionStatus.COMPLETED
        assert completed_insp.recommendation == InspectionRecommendation.SATISFACTORY
        assert completed_insp.geo_latitude == 19.0760

        await session.refresh(app)
        assert app.status == ApplicationStatus.INSPECTION_COMPLETED


@pytest.mark.asyncio
async def test_approval_and_rejection_determinations():
    """Fragment 89: Final statutory determinations with certificate grant and rejection grounds."""
    async with AsyncSessionLocal() as session:
        user, officer, inspector, dept, approval, biz, req = await _create_test_fixtures(session)

        # 1. Approval flow
        app = await ApplicationWorkflowService.create_application(
            session, ApplicationCreate(business_id=biz.id, approval_id=approval.id), user
        )
        await ApplicationWorkflowService.submit_application(
            session, app.id, ApplicationSubmitPayload(fee_paid=True, fee_reference="REC-003"), user
        )
        await ApplicationWorkflowService.start_review(session, app.id, officer)

        approved_app = await ApplicationWorkflowService.determine_application(
            session,
            app.id,
            StatutoryDeterminationPayload(decision="APPROVED", remarks="All statutory requirements fulfilled.", validity_years=5),
            officer,
        )
        assert approved_app.status == ApplicationStatus.APPROVED
        assert approved_app.approval_certificate_number.startswith("CERT-SPCB-")
        assert approved_app.validity_years == 5
        assert approved_app.certificate_valid_until is not None

        await session.refresh(req)
        assert req.status == RequirementStatus.APPROVED

        # 2. Rejection flow on separate clearance
        app2_approval = Approval(
            code="BOILER_REG",
            title="Boiler Registration",
            department_code="SPCB",
            issuing_authority="Boiler Directorate",
        )
        session.add(app2_approval)
        await session.commit()

        app2 = await ApplicationWorkflowService.create_application(
            session, ApplicationCreate(business_id=biz.id, approval_id=app2_approval.id), user
        )
        await ApplicationWorkflowService.submit_application(
            session, app2.id, ApplicationSubmitPayload(fee_paid=True, fee_reference="REC-004"), user
        )
        await ApplicationWorkflowService.start_review(session, app2.id, officer)

        # Rejection without reason fails
        with pytest.raises(ValidationError):
            await ApplicationWorkflowService.determine_application(
                session,
                app2.id,
                StatutoryDeterminationPayload(decision="REJECTED", rejection_reason=""),
                officer,
            )

        rejected_app = await ApplicationWorkflowService.determine_application(
            session,
            app2.id,
            StatutoryDeterminationPayload(
                decision="REJECTED",
                rejection_reason="Boiler design pressure exceeds allowable safety threshold for standard ISI shell.",
            ),
            officer,
        )
        assert rejected_app.status == ApplicationStatus.REJECTED
        assert "safety threshold" in rejected_app.rejection_reason


@pytest.mark.asyncio
async def test_rbac_security_boundaries():
    """Verify cross-tenant security and departmental isolation."""
    async with AsyncSessionLocal() as session:
        user, officer, inspector, dept, approval, biz, req = await _create_test_fixtures(session)

        # Another industry user
        other_user = User(
            email="intruder@other.com",
            hashed_password="pw",
            full_name="Other User",
            role=UserRole.INDUSTRY_USER,
        )
        # Officer from another department (e.g. FIRE)
        fire_officer = User(
            email="officer@fire.gov.in",
            hashed_password="pw",
            full_name="Fire Chief",
            role=UserRole.DEPARTMENT_OFFICER,
            department_id="FIRE",
        )
        session.add_all([other_user, fire_officer])
        await session.commit()

        app = await ApplicationWorkflowService.create_application(
            session, ApplicationCreate(business_id=biz.id, approval_id=approval.id), user
        )

        # Other user cannot submit app
        with pytest.raises(AuthorizationError):
            await ApplicationWorkflowService.submit_application(
                session, app.id, ApplicationSubmitPayload(fee_paid=True, fee_reference="REC"), other_user
            )

        # Other user cannot view application detail
        with pytest.raises(AuthorizationError):
            await ApplicationWorkflowService.get_application_detail(session, app.id, other_user)

        # Submit app
        await ApplicationWorkflowService.submit_application(
            session, app.id, ApplicationSubmitPayload(fee_paid=True, fee_reference="REC"), user
        )

        # FIRE officer cannot review SPCB clearance
        with pytest.raises(AuthorizationError) as exc_info:
            await ApplicationWorkflowService.start_review(session, app.id, fire_officer)
        assert "cannot review clearance" in str(exc_info.value)
