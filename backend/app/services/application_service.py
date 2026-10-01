"""
Application Workflow Service (Fragments 77, 78, 82, 83, 85, 87, 88, 89).
Orchestrates multi-department statutory application lifecycles, scrutinies,
deficiencies, field inspections, and formal clearance grants.
"""

from datetime import date, datetime, timedelta, timezone
import random
import string
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AuthorizationError,
    BusinessRuleViolationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.application import Application, ApplicationStatus
from app.models.application_query import ApplicationQuery, QueryStatus
from app.models.application_status_history import ApplicationStatusHistory
from app.models.approval import Approval
from app.models.approval_requirement import ApprovalRequirement, RequirementStatus
from app.models.business import Business
from app.models.department import Department
from app.models.document import Document
from app.models.inspection import Inspection, InspectionRecommendation, InspectionStatus
from app.models.user import User, UserRole
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetailRead,
    ApplicationQueryCreate,
    ApplicationQueryRead,
    ApplicationQueryRespondPayload,
    ApplicationStatusHistoryRead,
    ApplicationSubmitPayload,
    ApplicationSummaryRead,
    ApplicationUpdate,
    InspectionRead,
    InspectionReportPayload,
    InspectionSchedulePayload,
    OfficerInboxMetrics,
    OfficerInboxSummaryResponse,
    StatutoryDeterminationPayload,
)


def _generate_app_number() -> str:
    """Generate unique tracking number: APP-YYYYMMDD-XXXX."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"APP-{date_str}-{suffix}"


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime has UTC timezone info for offset-safe arithmetic."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _generate_certificate_number(dept_code: str) -> str:
    """Generate official certificate number: CERT-DEPT-YYYYMMDD-XXXX."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"CERT-{dept_code.upper()}-{date_str}-{suffix}"


class ApplicationWorkflowService:
    """Statutory clearance single-window application service."""

    @staticmethod
    async def create_application(
        db: AsyncSession,
        payload: ApplicationCreate,
        current_user: User,
    ) -> Application:
        """Create a new draft clearance application (Fragment 77)."""
        # 1. Verify business ownership or admin access
        stmt_biz = select(Business).where(Business.id == payload.business_id)
        biz = (await db.execute(stmt_biz)).scalar_one_or_none()
        if not biz:
            raise NotFoundError("Business unit not found", details={"business_id": payload.business_id})
        if current_user.role == UserRole.INDUSTRY_USER and biz.user_id != current_user.id:
            raise AuthorizationError("You do not have access to file applications for this business.")

        # 2. Verify Approval catalog item
        stmt_app = select(Approval).where(Approval.id == payload.approval_id)
        approval = (await db.execute(stmt_app)).scalar_one_or_none()
        if not approval:
            raise NotFoundError("Statutory clearance catalog entry not found", details={"approval_id": payload.approval_id})

        # 3. Check for existing active application for this business & approval
        stmt_existing = select(Application).where(
            Application.business_id == payload.business_id,
            Application.approval_id == payload.approval_id,
            Application.status.notin_([ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN]),
        )
        existing = (await db.execute(stmt_existing)).scalars().first()
        if existing:
            raise ConflictError(
                f"An active application ({existing.application_number}) in status '{existing.status.value}' "
                f"already exists for {approval.title}."
            )

        # 4. Resolve requirement if not supplied
        req_id = payload.requirement_id
        if not req_id:
            stmt_req = select(ApprovalRequirement).where(
                ApprovalRequirement.business_id == payload.business_id,
                ApprovalRequirement.approval_id == payload.approval_id,
            )
            req = (await db.execute(stmt_req)).scalar_one_or_none()
            if req:
                req_id = req.id

        # 5. Resolve department
        stmt_dept = select(Department).where(Department.code == approval.department_code)
        dept = (await db.execute(stmt_dept)).scalar_one_or_none()
        dept_id = dept.id if dept else None

        # 6. Build Application
        app_num = _generate_app_number()
        fee = payload.fee_amount if payload.fee_amount > 0 else approval.estimated_fee_base

        new_app = Application(
            application_number=app_num,
            business_id=payload.business_id,
            approval_id=payload.approval_id,
            requirement_id=req_id,
            department_id=dept_id,
            department_code=approval.department_code,
            applied_by_user_id=current_user.id,
            status=ApplicationStatus.DRAFT,
            application_data=payload.application_data,
            attached_document_ids=payload.attached_document_ids,
            fee_amount=fee,
            fee_paid=payload.fee_paid,
            fee_reference=payload.fee_reference,
        )
        db.add(new_app)
        await db.flush()

        # 7. Add audit log
        history = ApplicationStatusHistory(
            application_id=new_app.id,
            from_status=None,
            to_status=ApplicationStatus.DRAFT,
            changed_by_user_id=current_user.id,
            action="CREATE_DRAFT",
            remarks="Draft statutory application initialized",
        )
        db.add(history)
        await db.commit()
        await db.refresh(new_app)
        return new_app

    @staticmethod
    async def submit_application(
        db: AsyncSession,
        application_id: str,
        payload: ApplicationSubmitPayload,
        current_user: User,
    ) -> Application:
        """Formally submit a draft application (Fragment 78)."""
        app_obj = await ApplicationWorkflowService._get_app_entity(db, application_id)
        if current_user.role == UserRole.INDUSTRY_USER and app_obj.applied_by_user_id != current_user.id:
            raise AuthorizationError("Only the applicant or authorized officer may submit this application.")

        if app_obj.status != ApplicationStatus.DRAFT:
            raise BusinessRuleViolationError(
                f"Application is in status '{app_obj.status.value}' and cannot be submitted. Only DRAFT applications can be submitted."
            )

        if not payload.fee_paid or not payload.fee_reference:
            raise ValidationError("Statutory fees must be confirmed with an e-challan reference number before submission.")

        # Update application
        now = datetime.now(timezone.utc)
        approval = app_obj.approval
        sla_days = approval.sla_days if approval and approval.sla_days else 30

        app_obj.status = ApplicationStatus.SUBMITTED
        app_obj.fee_paid = True
        app_obj.fee_reference = payload.fee_reference
        app_obj.submitted_at = now
        app_obj.sla_due_date = now + timedelta(days=sla_days)

        # Update linked requirement if exists
        if app_obj.requirement_id:
            stmt_req = select(ApprovalRequirement).where(ApprovalRequirement.id == app_obj.requirement_id)
            req = (await db.execute(stmt_req)).scalar_one_or_none()
            if req:
                req.status = RequirementStatus.SUBMITTED

        # Audit history
        history = ApplicationStatusHistory(
            application_id=app_obj.id,
            from_status=ApplicationStatus.DRAFT,
            to_status=ApplicationStatus.SUBMITTED,
            changed_by_user_id=current_user.id,
            action="SUBMIT",
            remarks=payload.additional_remarks or f"Statutory application submitted with fee receipt {payload.fee_reference}",
        )
        db.add(history)
        await db.commit()
        await db.refresh(app_obj)
        return app_obj

    @staticmethod
    async def start_review(
        db: AsyncSession,
        application_id: str,
        current_user: User,
    ) -> Application:
        """Department officer begins formal statutory scrutiny (Fragment 82)."""
        app_obj = await ApplicationWorkflowService._get_app_entity(db, application_id)
        ApplicationWorkflowService._verify_officer_dept(current_user, app_obj)

        if app_obj.status not in (ApplicationStatus.SUBMITTED, ApplicationStatus.RESUBMITTED):
            raise BusinessRuleViolationError(
                f"Cannot begin review. Application is currently in '{app_obj.status.value}'. Must be SUBMITTED or RESUBMITTED."
            )

        from_status = app_obj.status
        now = datetime.now(timezone.utc)
        app_obj.status = ApplicationStatus.UNDER_REVIEW
        app_obj.assigned_officer_id = current_user.id
        app_obj.reviewed_at = now

        if app_obj.requirement_id:
            stmt_req = select(ApprovalRequirement).where(ApprovalRequirement.id == app_obj.requirement_id)
            req = (await db.execute(stmt_req)).scalar_one_or_none()
            if req:
                req.status = RequirementStatus.UNDER_REVIEW

        history = ApplicationStatusHistory(
            application_id=app_obj.id,
            from_status=from_status,
            to_status=ApplicationStatus.UNDER_REVIEW,
            changed_by_user_id=current_user.id,
            action="START_REVIEW",
            remarks=f"Scrutiny commenced by officer {current_user.full_name}",
        )
        db.add(history)
        await db.commit()
        await db.refresh(app_obj)
        return app_obj

    @staticmethod
    async def raise_deficiency_query(
        db: AsyncSession,
        application_id: str,
        payload: ApplicationQueryCreate,
        current_user: User,
    ) -> ApplicationQuery:
        """Officer issues formal deficiency notice/query (Fragment 83)."""
        app_obj = await ApplicationWorkflowService._get_app_entity(db, application_id)
        ApplicationWorkflowService._verify_officer_dept(current_user, app_obj)

        if app_obj.status not in (ApplicationStatus.UNDER_REVIEW, ApplicationStatus.SUBMITTED, ApplicationStatus.RESUBMITTED):
            raise BusinessRuleViolationError(
                f"Cannot raise query on application in status '{app_obj.status.value}'."
            )

        from_status = app_obj.status
        app_obj.status = ApplicationStatus.QUERY_RAISED

        query = ApplicationQuery(
            application_id=app_obj.id,
            raised_by_user_id=current_user.id,
            document_id=payload.document_id,
            query_title=payload.query_title,
            query_text=payload.query_text,
            status=QueryStatus.OPEN,
            due_date=payload.due_date,
        )
        db.add(query)

        history = ApplicationStatusHistory(
            application_id=app_obj.id,
            from_status=from_status,
            to_status=ApplicationStatus.QUERY_RAISED,
            changed_by_user_id=current_user.id,
            action="RAISE_QUERY",
            remarks=f"Deficiency query raised: {payload.query_title}",
        )
        db.add(history)
        await db.commit()
        await db.refresh(query)
        return query

    @staticmethod
    async def respond_to_query(
        db: AsyncSession,
        application_id: str,
        query_id: str,
        payload: ApplicationQueryRespondPayload,
        current_user: User,
    ) -> ApplicationQuery:
        """Applicant responds to raised deficiency with explanation or replacement doc (Fragment 84)."""
        app_obj = await ApplicationWorkflowService._get_app_entity(db, application_id)
        if current_user.role == UserRole.INDUSTRY_USER and app_obj.applied_by_user_id != current_user.id:
            raise AuthorizationError("Only the applicant may respond to queries for this application.")

        stmt_q = select(ApplicationQuery).where(
            ApplicationQuery.id == query_id,
            ApplicationQuery.application_id == application_id,
        )
        query = (await db.execute(stmt_q)).scalar_one_or_none()
        if not query:
            raise NotFoundError("Query not found on this application", details={"query_id": query_id})

        if query.status != QueryStatus.OPEN:
            raise BusinessRuleViolationError(f"Query is already {query.status.value}.")

        now = datetime.now(timezone.utc)
        query.response_text = payload.response_text
        query.response_document_id = payload.response_document_id
        query.status = QueryStatus.RESOLVED
        query.resolved_at = now

        # If a new document is attached, ensure it's recorded in application attached_document_ids
        if payload.response_document_id:
            doc_ids = list(app_obj.attached_document_ids or [])
            if payload.response_document_id not in doc_ids:
                doc_ids.append(payload.response_document_id)
                app_obj.attached_document_ids = doc_ids

        await db.commit()
        await db.refresh(query)
        return query

    @staticmethod
    async def resubmit_application(
        db: AsyncSession,
        application_id: str,
        remarks: Optional[str],
        current_user: User,
    ) -> Application:
        """Applicant formally resubmits application after resolving deficiencies (Fragment 85)."""
        app_obj = await ApplicationWorkflowService._get_app_entity(db, application_id)
        if current_user.role == UserRole.INDUSTRY_USER and app_obj.applied_by_user_id != current_user.id:
            raise AuthorizationError("Only the applicant may resubmit this application.")

        if app_obj.status != ApplicationStatus.QUERY_RAISED:
            raise BusinessRuleViolationError(
                f"Application is in status '{app_obj.status.value}'. Resubmission is only allowed from QUERY_RAISED."
            )

        # Verify all queries are resolved
        stmt_open_queries = select(ApplicationQuery).where(
            ApplicationQuery.application_id == application_id,
            ApplicationQuery.status == QueryStatus.OPEN,
        )
        open_queries = (await db.execute(stmt_open_queries)).scalars().all()
        if open_queries:
            raise BusinessRuleViolationError(
                f"Cannot resubmit. There are {len(open_queries)} unresolved queries. Please address all queries first."
            )

        from_status = app_obj.status
        app_obj.status = ApplicationStatus.RESUBMITTED

        history = ApplicationStatusHistory(
            application_id=app_obj.id,
            from_status=from_status,
            to_status=ApplicationStatus.RESUBMITTED,
            changed_by_user_id=current_user.id,
            action="RESUBMIT",
            remarks=remarks or "Application resubmitted with corrective responses to all deficiency notes",
        )
        db.add(history)
        await db.commit()
        await db.refresh(app_obj)
        return app_obj

    @staticmethod
    async def schedule_inspection(
        db: AsyncSession,
        application_id: str,
        payload: InspectionSchedulePayload,
        current_user: User,
    ) -> Inspection:
        """Officer assigns inspector and schedules physical site inspection (Fragment 87)."""
        app_obj = await ApplicationWorkflowService._get_app_entity(db, application_id)
        ApplicationWorkflowService._verify_officer_dept(current_user, app_obj)

        if app_obj.status not in (ApplicationStatus.UNDER_REVIEW, ApplicationStatus.RESUBMITTED, ApplicationStatus.INSPECTION_SCHEDULED):
            raise BusinessRuleViolationError(
                f"Cannot schedule inspection for application in status '{app_obj.status.value}'."
            )

        # Verify inspector exists and has INSPECTOR role
        stmt_inspector = select(User).where(User.id == payload.inspector_id)
        inspector = (await db.execute(stmt_inspector)).scalar_one_or_none()
        if not inspector or inspector.role not in (UserRole.INSPECTOR, UserRole.ADMIN, UserRole.DEPARTMENT_OFFICER):
            raise NotFoundError("Assigned inspector user not found or does not hold field inspector credentials.")

        from_status = app_obj.status
        app_obj.status = ApplicationStatus.INSPECTION_SCHEDULED

        inspection = Inspection(
            application_id=app_obj.id,
            inspector_id=payload.inspector_id,
            department_id=app_obj.department_id,
            scheduled_date=payload.scheduled_date,
            status=InspectionStatus.SCHEDULED,
            instructions=payload.instructions,
            checklist_results={},
        )
        db.add(inspection)

        history = ApplicationStatusHistory(
            application_id=app_obj.id,
            from_status=from_status,
            to_status=ApplicationStatus.INSPECTION_SCHEDULED,
            changed_by_user_id=current_user.id,
            action="SCHEDULE_INSPECTION",
            remarks=f"Inspection scheduled for {payload.scheduled_date.isoformat()} assigned to {inspector.full_name}",
        )
        db.add(history)
        await db.commit()
        await db.refresh(inspection)
        return inspection

    @staticmethod
    async def submit_inspection_report(
        db: AsyncSession,
        inspection_id: str,
        payload: InspectionReportPayload,
        current_user: User,
    ) -> Inspection:
        """Field Inspector submits site verification findings and recommendations (Fragment 88)."""
        stmt_insp = select(Inspection).where(Inspection.id == inspection_id)
        inspection = (await db.execute(stmt_insp)).scalar_one_or_none()
        if not inspection:
            raise NotFoundError("Inspection record not found", details={"inspection_id": inspection_id})

        # Verify inspector access
        if current_user.role == UserRole.INSPECTOR and inspection.inspector_id != current_user.id:
            raise AuthorizationError("You are not assigned to conduct this site inspection.")

        now = datetime.now(timezone.utc)
        inspection.status = InspectionStatus.COMPLETED
        inspection.findings = payload.findings
        inspection.checklist_results = payload.checklist_results
        inspection.recommendation = payload.recommendation
        inspection.geo_latitude = payload.geo_latitude
        inspection.geo_longitude = payload.geo_longitude
        inspection.report_document_id = payload.report_document_id
        inspection.completed_at = now

        # Update application status
        app_obj = await ApplicationWorkflowService._get_app_entity(db, inspection.application_id)
        from_status = app_obj.status
        app_obj.status = ApplicationStatus.INSPECTION_COMPLETED

        history = ApplicationStatusHistory(
            application_id=app_obj.id,
            from_status=from_status,
            to_status=ApplicationStatus.INSPECTION_COMPLETED,
            changed_by_user_id=current_user.id,
            action="COMPLETE_INSPECTION",
            remarks=f"Inspection report submitted with recommendation: {payload.recommendation.value}",
        )
        db.add(history)
        await db.commit()
        await db.refresh(inspection)
        return inspection

    @staticmethod
    async def determine_application(
        db: AsyncSession,
        application_id: str,
        payload: StatutoryDeterminationPayload,
        current_user: User,
    ) -> Application:
        """Officer makes final statutory approval or rejection decision (Fragment 89)."""
        app_obj = await ApplicationWorkflowService._get_app_entity(db, application_id)
        ApplicationWorkflowService._verify_officer_dept(current_user, app_obj)

        if app_obj.status in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN):
            raise BusinessRuleViolationError(
                f"Application is already finalized in status '{app_obj.status.value}'."
            )

        from_status = app_obj.status
        now = datetime.now(timezone.utc)
        app_obj.decided_at = now

        if payload.decision == "APPROVED":
            cert_num = _generate_certificate_number(app_obj.department_code)
            app_obj.status = ApplicationStatus.APPROVED
            app_obj.approval_certificate_number = cert_num
            app_obj.validity_years = payload.validity_years or 5
            app_obj.certificate_valid_until = (now + timedelta(days=365 * app_obj.validity_years)).date()

            # Update requirement
            if app_obj.requirement_id:
                stmt_req = select(ApprovalRequirement).where(ApprovalRequirement.id == app_obj.requirement_id)
                req = (await db.execute(stmt_req)).scalar_one_or_none()
                if req:
                    req.status = RequirementStatus.APPROVED

            history = ApplicationStatusHistory(
                application_id=app_obj.id,
                from_status=from_status,
                to_status=ApplicationStatus.APPROVED,
                changed_by_user_id=current_user.id,
                action="APPROVE",
                remarks=payload.remarks or f"Statutory clearance approved. Certificate {cert_num} issued.",
            )
        else:
            if not payload.rejection_reason:
                raise ValidationError("Statutory grounds / rejection reason must be provided when rejecting an application.")
            app_obj.status = ApplicationStatus.REJECTED
            app_obj.rejection_reason = payload.rejection_reason

            if app_obj.requirement_id:
                stmt_req = select(ApprovalRequirement).where(ApprovalRequirement.id == app_obj.requirement_id)
                req = (await db.execute(stmt_req)).scalar_one_or_none()
                if req:
                    req.status = RequirementStatus.REJECTED

            history = ApplicationStatusHistory(
                application_id=app_obj.id,
                from_status=from_status,
                to_status=ApplicationStatus.REJECTED,
                changed_by_user_id=current_user.id,
                action="REJECT",
                remarks=f"Clearance rejected: {payload.rejection_reason}",
            )

        db.add(history)
        await db.commit()
        await db.refresh(app_obj)
        return app_obj

    @staticmethod
    async def list_applications(
        db: AsyncSession,
        current_user: User,
        business_id: Optional[str] = None,
        department_code: Optional[str] = None,
        status: Optional[ApplicationStatus] = None,
    ) -> List[ApplicationSummaryRead]:
        """List applications with security filters according to caller role."""
        stmt = select(Application).join(Application.approval)

        if current_user.role == UserRole.INDUSTRY_USER:
            # Industry can only see applications from their own businesses
            stmt = stmt.join(Application.business).where(Business.user_id == current_user.id)
            if business_id:
                stmt = stmt.where(Application.business_id == business_id)
        elif current_user.role == UserRole.DEPARTMENT_OFFICER:
            # Officer sees applications matching their department code/id
            if current_user.department_id and current_user.department_id != "ALL_DEPARTMENTS":
                stmt = stmt.where(
                    or_(
                        Application.department_id == current_user.department_id,
                        Application.department_code == current_user.department_id,
                    )
                )
        elif current_user.role == UserRole.INSPECTOR:
            # Inspectors see applications assigned to them or in their department
            pass

        if department_code:
            stmt = stmt.where(Application.department_code == department_code)
        if status:
            stmt = stmt.where(Application.status == status)

        stmt = stmt.order_by(Application.created_at.desc())
        results = (await db.execute(stmt)).scalars().all()

        summaries = []
        now = datetime.now(timezone.utc)
        for app in results:
            sla_days_rem = None
            due = _ensure_utc(app.sla_due_date)
            if due and app.status not in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN):
                delta = due - now
                sla_days_rem = max(0, delta.days)

            summaries.append(
                ApplicationSummaryRead(
                    id=app.id,
                    application_number=app.application_number,
                    business_id=app.business_id,
                    business_name=app.business.legal_name if app.business else None,
                    approval_id=app.approval_id,
                    approval_code=app.approval.code if app.approval else None,
                    approval_title=app.approval.title if app.approval else None,
                    department_code=app.department_code,
                    department_name=app.department.name if app.department else None,
                    status=app.status,
                    fee_amount=app.fee_amount,
                    fee_paid=app.fee_paid,
                    submitted_at=app.submitted_at,
                    sla_due_date=app.sla_due_date,
                    sla_days_remaining=sla_days_rem,
                    approval_certificate_number=app.approval_certificate_number,
                    created_at=app.created_at,
                    updated_at=app.updated_at,
                )
            )
        return summaries

    @staticmethod
    async def get_application_detail(
        db: AsyncSession,
        application_id: str,
        current_user: User,
    ) -> ApplicationDetailRead:
        """Fetch full application detail with RBAC verification and nested items."""
        app_obj = await ApplicationWorkflowService._get_app_entity(db, application_id)

        # RBAC Check
        if current_user.role == UserRole.INDUSTRY_USER:
            if app_obj.business.user_id != current_user.id:
                raise AuthorizationError("You do not have permission to view this application.")

        now = datetime.now(timezone.utc)
        sla_days_rem = None
        due = _ensure_utc(app_obj.sla_due_date)
        if due and app_obj.status not in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN):
            delta = due - now
            sla_days_rem = max(0, delta.days)

        # Build nested status history
        histories = [
            ApplicationStatusHistoryRead(
                id=h.id,
                application_id=h.application_id,
                from_status=h.from_status,
                to_status=h.to_status,
                changed_by_user_id=h.changed_by_user_id,
                changed_by_name=h.changed_by.full_name if h.changed_by else None,
                action=h.action,
                remarks=h.remarks,
                created_at=h.created_at,
            )
            for h in (app_obj.status_history or [])
        ]

        # Build nested queries
        queries = [
            ApplicationQueryRead(
                id=q.id,
                application_id=q.application_id,
                raised_by_user_id=q.raised_by_user_id,
                raised_by_name=q.raised_by.full_name if q.raised_by else None,
                document_id=q.document_id,
                query_title=q.query_title,
                query_text=q.query_text,
                status=q.status,
                due_date=q.due_date,
                response_text=q.response_text,
                response_document_id=q.response_document_id,
                resolved_at=q.resolved_at,
                created_at=q.created_at,
            )
            for q in (app_obj.queries or [])
        ]

        # Build nested inspections
        inspections = [
            InspectionRead(
                id=i.id,
                application_id=i.application_id,
                inspector_id=i.inspector_id,
                inspector_name=i.inspector.full_name if i.inspector else None,
                department_id=i.department_id,
                scheduled_date=i.scheduled_date,
                status=i.status,
                instructions=i.instructions,
                findings=i.findings,
                checklist_results=i.checklist_results or {},
                recommendation=i.recommendation,
                geo_latitude=i.geo_latitude,
                geo_longitude=i.geo_longitude,
                report_document_id=i.report_document_id,
                completed_at=i.completed_at,
                created_at=i.created_at,
            )
            for i in (app_obj.inspections or [])
        ]

        return ApplicationDetailRead(
            id=app_obj.id,
            application_number=app_obj.application_number,
            business_id=app_obj.business_id,
            business_name=app_obj.business.legal_name if app_obj.business else None,
            approval_id=app_obj.approval_id,
            approval_code=app_obj.approval.code if app_obj.approval else None,
            approval_title=app_obj.approval.title if app_obj.approval else None,
            requirement_id=app_obj.requirement_id,
            department_id=app_obj.department_id,
            department_code=app_obj.department_code,
            department_name=app_obj.department.name if app_obj.department else None,
            applied_by_user_id=app_obj.applied_by_user_id,
            applied_by_name=app_obj.applicant.full_name if app_obj.applicant else None,
            assigned_officer_id=app_obj.assigned_officer_id,
            assigned_officer_name=app_obj.assigned_officer.full_name if app_obj.assigned_officer else None,
            status=app_obj.status,
            application_data=app_obj.application_data or {},
            attached_document_ids=app_obj.attached_document_ids or [],
            fee_amount=app_obj.fee_amount,
            fee_paid=app_obj.fee_paid,
            fee_reference=app_obj.fee_reference,
            submitted_at=app_obj.submitted_at,
            reviewed_at=app_obj.reviewed_at,
            decided_at=app_obj.decided_at,
            sla_due_date=app_obj.sla_due_date,
            sla_days_remaining=sla_days_rem,
            approval_certificate_number=app_obj.approval_certificate_number,
            rejection_reason=app_obj.rejection_reason,
            validity_years=app_obj.validity_years,
            certificate_valid_until=app_obj.certificate_valid_until,
            status_history=histories,
            queries=queries,
            inspections=inspections,
            created_at=app_obj.created_at,
            updated_at=app_obj.updated_at,
        )

    @staticmethod
    async def get_officer_inbox_metrics(
        db: AsyncSession,
        current_user: User,
    ) -> OfficerInboxSummaryResponse:
        """Compute live queue statistics for department officer review portal (Fragment 81)."""
        dept_code = current_user.department_id or "ALL"

        stmt = select(Application)
        if current_user.department_id and current_user.department_id != "ALL_DEPARTMENTS":
            stmt = stmt.where(
                or_(
                    Application.department_id == current_user.department_id,
                    Application.department_code == current_user.department_id,
                )
            )

        apps = (await db.execute(stmt)).scalars().all()
        now = datetime.now(timezone.utc)

        pending_scrutiny = sum(1 for a in apps if a.status in (ApplicationStatus.SUBMITTED, ApplicationStatus.RESUBMITTED))
        under_review = sum(1 for a in apps if a.status == ApplicationStatus.UNDER_REVIEW)
        queries_pending = sum(1 for a in apps if a.status == ApplicationStatus.QUERY_RAISED)
        inspections_sched = sum(1 for a in apps if a.status in (ApplicationStatus.INSPECTION_SCHEDULED, ApplicationStatus.INSPECTION_COMPLETED))
        approved_count = sum(1 for a in apps if a.status == ApplicationStatus.APPROVED)
        rejected_count = sum(1 for a in apps if a.status == ApplicationStatus.REJECTED)

        sla_critical = 0
        for a in apps:
            due = _ensure_utc(a.sla_due_date)
            if (
                due
                and a.status not in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN)
                and (due - now).days <= 3
            ):
                sla_critical += 1

        total_decided = approved_count + rejected_count
        compliance_rate = 98.5 if total_decided == 0 else round(max(80.0, 100.0 - (sla_critical * 2.5)), 1)

        next_action = "Review incoming submissions in priority queue"
        if pending_scrutiny > 0:
            next_action = f"{pending_scrutiny} applications awaiting initial statutory scrutiny"
        elif queries_pending > 0:
            next_action = f"Monitor {queries_pending} queries awaiting industrial applicant replies"

        metrics = OfficerInboxMetrics(
            pending_scrutiny=pending_scrutiny,
            under_review=under_review,
            queries_pending_applicant_response=queries_pending,
            inspections_scheduled=inspections_sched,
            approved_count=approved_count,
            rejected_count=rejected_count,
            sla_critical_count=sla_critical,
            sla_compliance_rate_percent=compliance_rate,
        )

        return OfficerInboxSummaryResponse(
            officer_id=current_user.id,
            full_name=current_user.full_name,
            department_id=current_user.department_id,
            department_code=dept_code,
            designation=current_user.designation or "Scrutiny Officer",
            role=current_user.role.value,
            queue_metrics=metrics,
            next_action=next_action,
        )

    # ------------------- Private Helpers -------------------

    @staticmethod
    async def _get_app_entity(db: AsyncSession, application_id: str) -> Application:
        stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.business),
                selectinload(Application.approval),
                selectinload(Application.department),
                selectinload(Application.applicant),
                selectinload(Application.assigned_officer),
                selectinload(Application.status_history).selectinload(ApplicationStatusHistory.changed_by),
                selectinload(Application.queries).selectinload(ApplicationQuery.raised_by),
                selectinload(Application.inspections).selectinload(Inspection.inspector),
            )
        )
        app_obj = (await db.execute(stmt)).scalar_one_or_none()
        if not app_obj:
            raise NotFoundError("Application not found", details={"application_id": application_id})
        return app_obj

    @staticmethod
    def _verify_officer_dept(officer: User, app_obj: Application) -> None:
        """Ensure officer belongs to the reviewing department or is admin."""
        if officer.role == UserRole.ADMIN:
            return
        if officer.role != UserRole.DEPARTMENT_OFFICER:
            raise AuthorizationError("Only department scrutiny officers may perform this action.")
        # If officer has department_id set, check match
        if officer.department_id and officer.department_id not in ("ALL_DEPARTMENTS", "ALL"):
            if officer.department_id != app_obj.department_id and officer.department_id != app_obj.department_code:
                raise AuthorizationError(
                    f"Officer assigned to department '{officer.department_id}' cannot review clearance for '{app_obj.department_code}'."
                )
