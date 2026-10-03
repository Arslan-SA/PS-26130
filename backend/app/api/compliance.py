"""
Compliance REST API endpoints (Phase 7, Fragment 100).

Provides:
- Industry users: compliance dashboard, alerts, prioritized action queue,
  filing submissions, compliance status overview.
- Officers: compliance filing review/approval.
- Admin: seed compliance requirements, list all requirements.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_active_user,
    require_admin,
    require_industry_user,
    require_officer,
)
from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.compliance import ComplianceCategory, ComplianceRecordStatus
from app.models.user import User, UserRole
from app.schemas.compliance import (
    ComplianceAlertListResponse,
    ComplianceDashboardMetrics,
    CompliancePrioritizedListResponse,
    ComplianceRecordCreate,
    ComplianceRecordListResponse,
    ComplianceRecordRead,
    ComplianceRecordSubmitPayload,
    ComplianceRecordReviewPayload,
    ComplianceRecordSummary,
    ComplianceRequirementListResponse,
    ComplianceRequirementRead,
    ComplianceStatusResponse,
)
from app.services.compliance_service import (
    create_renewal_from_application,
    evaluate_business_compliance_requirements,
    generate_compliance_records_for_business,
    get_all_compliance_requirements,
    get_compliance_alerts,
    get_compliance_dashboard,
    get_compliance_record_by_id,
    get_compliance_records,
    get_prioritized_compliance,
    get_compliance_status,
    review_compliance_filing,
    seed_compliance_requirements,
    submit_compliance_filing,
)

logger = logging.getLogger("udyamsetu.api.compliance")

router = APIRouter(prefix="/compliance", tags=["Compliance & Monitoring"])


# ---------------------------------------------------------------------------
# Admin: Seed & List Requirements
# ---------------------------------------------------------------------------

@router.post(
    "/requirements/seed",
    response_model=ComplianceRequirementListResponse,
    summary="Seed compliance requirement catalog",
    description="Administrative endpoint to populate the compliance requirements catalog from built-in rules.",
)
async def seed_requirements(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    created = await seed_compliance_requirements(db)
    all_reqs = await get_all_compliance_requirements(db)
    return ComplianceRequirementListResponse(
        total=len(all_reqs),
        items=[ComplianceRequirementRead.model_validate(r) for r in all_reqs],
    )


@router.get(
    "/requirements",
    response_model=ComplianceRequirementListResponse,
    summary="List all compliance requirements",
    description="Fetch the full compliance obligations catalog.",
)
async def list_requirements(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    all_reqs = await get_all_compliance_requirements(db)
    return ComplianceRequirementListResponse(
        total=len(all_reqs),
        items=[ComplianceRequirementRead.model_validate(r) for r in all_reqs],
    )


# ---------------------------------------------------------------------------
# Industry: Evaluate & Generate Compliance Records
# ---------------------------------------------------------------------------

@router.post(
    "/businesses/{business_id}/evaluate",
    response_model=ComplianceRequirementListResponse,
    summary="Evaluate applicable compliance requirements",
    description="Determine which compliance obligations apply to a business based on its profile.",
)
async def evaluate_compliance(
    business_id: str,
    current_user: User = Depends(require_industry_user),
    db: AsyncSession = Depends(get_db),
):
    applicable = await evaluate_business_compliance_requirements(db, business_id)
    return ComplianceRequirementListResponse(
        total=len(applicable),
        items=[ComplianceRequirementRead.model_validate(r) for r in applicable],
    )


@router.post(
    "/businesses/{business_id}/generate",
    response_model=ComplianceRecordListResponse,
    summary="Generate compliance tracking records",
    description="Create compliance tracking records for all applicable obligations for a business.",
)
async def generate_compliance(
    business_id: str,
    cycles_ahead: int = Query(1, ge=1, le=5, description="Number of future cycles to generate"),
    current_user: User = Depends(require_industry_user),
    db: AsyncSession = Depends(get_db),
):
    records = await generate_compliance_records_for_business(
        db, business_id, cycles_ahead=cycles_ahead
    )
    summaries = []
    for r in records:
        req = r.requirement
        summaries.append(ComplianceRecordSummary(
            id=r.id,
            business_id=r.business_id,
            requirement_id=r.requirement_id,
            status=r.status,
            cycle_label=r.cycle_label,
            due_date=r.due_date,
            days_overdue=r.days_overdue,
            requirement_code=req.code if req else None,
            requirement_title=req.title if req else None,
            requirement_category=req.category if req else None,
            requirement_priority=req.priority if req else None,
            penalty_imposed=r.penalty_imposed,
            created_at=r.created_at,
        ))
    return ComplianceRecordListResponse(total=len(summaries), items=summaries)


# ---------------------------------------------------------------------------
# Industry: Dashboard, Alerts, Status, Prioritized Queue
# ---------------------------------------------------------------------------

@router.get(
    "/businesses/{business_id}/dashboard",
    response_model=ComplianceDashboardMetrics,
    summary="Compliance dashboard metrics",
    description="Aggregate compliance health metrics for a business entity.",
)
async def compliance_dashboard(
    business_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_compliance_dashboard(db, business_id)


@router.get(
    "/businesses/{business_id}/alerts",
    response_model=ComplianceAlertListResponse,
    summary="Compliance alerts",
    description="Real-time compliance alert notifications for upcoming, overdue, and expiring obligations.",
)
async def compliance_alerts(
    business_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_compliance_alerts(db, business_id)


@router.get(
    "/businesses/{business_id}/status",
    response_model=ComplianceStatusResponse,
    summary="Compliance status report",
    description="Comprehensive compliance status with category breakdown and health rating.",
)
async def compliance_status(
    business_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_compliance_status(db, business_id)


@router.get(
    "/businesses/{business_id}/priorities",
    response_model=CompliancePrioritizedListResponse,
    summary="Prioritized compliance action queue",
    description="Ranked list of compliance items ordered by urgency score for action prioritization.",
)
async def compliance_priorities(
    business_id: str,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_prioritized_compliance(db, business_id, limit=limit)


# ---------------------------------------------------------------------------
# Industry: Compliance Records CRUD
# ---------------------------------------------------------------------------

@router.get(
    "/businesses/{business_id}/records",
    response_model=ComplianceRecordListResponse,
    summary="List compliance records",
    description="Fetch filtered compliance records for a business.",
)
async def list_compliance_records(
    business_id: str,
    status: Optional[ComplianceRecordStatus] = Query(None),
    category: Optional[ComplianceCategory] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    records, total = await get_compliance_records(
        db, business_id,
        status_filter=status,
        category_filter=category,
        limit=limit,
        offset=offset,
    )
    summaries = []
    for r in records:
        req = r.requirement
        summaries.append(ComplianceRecordSummary(
            id=r.id,
            business_id=r.business_id,
            requirement_id=r.requirement_id,
            status=r.status,
            cycle_label=r.cycle_label,
            due_date=r.due_date,
            days_overdue=r.days_overdue,
            requirement_code=req.code if req else None,
            requirement_title=req.title if req else None,
            requirement_category=req.category if req else None,
            requirement_priority=req.priority if req else None,
            penalty_imposed=r.penalty_imposed,
            created_at=r.created_at,
        ))
    return ComplianceRecordListResponse(total=total, items=summaries)


@router.get(
    "/records/{record_id}",
    response_model=ComplianceRecordRead,
    summary="Get compliance record detail",
    description="Fetch full detail of a single compliance record.",
)
async def get_record_detail(
    record_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    record = await get_compliance_record_by_id(db, record_id)
    req = record.requirement
    biz = record.business
    return ComplianceRecordRead(
        id=record.id,
        business_id=record.business_id,
        requirement_id=record.requirement_id,
        application_id=record.application_id,
        status=record.status,
        cycle_label=record.cycle_label,
        due_date=record.due_date,
        warning_date=record.warning_date,
        submitted_at=record.submitted_at,
        approved_at=record.approved_at,
        new_valid_until=record.new_valid_until,
        evidence_document_ids=record.evidence_document_ids,
        filing_data=record.filing_data,
        remarks=record.remarks,
        officer_remarks=record.officer_remarks,
        penalty_imposed=record.penalty_imposed,
        days_overdue=record.days_overdue,
        responsible_user_id=record.responsible_user_id,
        is_active=record.is_active,
        created_at=record.created_at,
        updated_at=record.updated_at,
        requirement_code=req.code if req else None,
        requirement_title=req.title if req else None,
        requirement_category=req.category if req else None,
        requirement_priority=req.priority if req else None,
        requirement_frequency=req.frequency if req else None,
        business_name=biz.legal_name if biz else None,
    )


# ---------------------------------------------------------------------------
# Industry: Submit Filing
# ---------------------------------------------------------------------------

@router.post(
    "/records/{record_id}/submit",
    response_model=ComplianceRecordRead,
    summary="Submit compliance filing",
    description="Industry user submits a compliance filing with evidence documents.",
)
async def submit_filing(
    record_id: str,
    payload: ComplianceRecordSubmitPayload,
    current_user: User = Depends(require_industry_user),
    db: AsyncSession = Depends(get_db),
):
    record = await submit_compliance_filing(
        db, record_id,
        filing_data=payload.filing_data,
        evidence_document_ids=payload.evidence_document_ids,
        remarks=payload.remarks,
        user_id=current_user.id,
    )
    req = record.requirement
    biz = record.business
    return ComplianceRecordRead(
        id=record.id,
        business_id=record.business_id,
        requirement_id=record.requirement_id,
        application_id=record.application_id,
        status=record.status,
        cycle_label=record.cycle_label,
        due_date=record.due_date,
        warning_date=record.warning_date,
        submitted_at=record.submitted_at,
        approved_at=record.approved_at,
        new_valid_until=record.new_valid_until,
        evidence_document_ids=record.evidence_document_ids,
        filing_data=record.filing_data,
        remarks=record.remarks,
        officer_remarks=record.officer_remarks,
        penalty_imposed=record.penalty_imposed,
        days_overdue=record.days_overdue,
        responsible_user_id=record.responsible_user_id,
        is_active=record.is_active,
        created_at=record.created_at,
        updated_at=record.updated_at,
        requirement_code=req.code if req else None,
        requirement_title=req.title if req else None,
        requirement_category=req.category if req else None,
        requirement_priority=req.priority if req else None,
        requirement_frequency=req.frequency if req else None,
        business_name=biz.legal_name if biz else None,
    )


# ---------------------------------------------------------------------------
# Officer: Review Filing
# ---------------------------------------------------------------------------

@router.post(
    "/records/{record_id}/review",
    response_model=ComplianceRecordRead,
    summary="Review compliance filing",
    description="Department officer reviews and approves/rejects a compliance filing.",
)
async def review_filing(
    record_id: str,
    payload: ComplianceRecordReviewPayload,
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db),
):
    record = await review_compliance_filing(
        db, record_id,
        decision=payload.decision,
        officer_remarks=payload.officer_remarks,
        new_valid_until=payload.new_valid_until,
        penalty_imposed=payload.penalty_imposed,
    )
    req = record.requirement
    biz = record.business
    return ComplianceRecordRead(
        id=record.id,
        business_id=record.business_id,
        requirement_id=record.requirement_id,
        application_id=record.application_id,
        status=record.status,
        cycle_label=record.cycle_label,
        due_date=record.due_date,
        warning_date=record.warning_date,
        submitted_at=record.submitted_at,
        approved_at=record.approved_at,
        new_valid_until=record.new_valid_until,
        evidence_document_ids=record.evidence_document_ids,
        filing_data=record.filing_data,
        remarks=record.remarks,
        officer_remarks=record.officer_remarks,
        penalty_imposed=record.penalty_imposed,
        days_overdue=record.days_overdue,
        responsible_user_id=record.responsible_user_id,
        is_active=record.is_active,
        created_at=record.created_at,
        updated_at=record.updated_at,
        requirement_code=req.code if req else None,
        requirement_title=req.title if req else None,
        requirement_category=req.category if req else None,
        requirement_priority=req.priority if req else None,
        requirement_frequency=req.frequency if req else None,
        business_name=biz.legal_name if biz else None,
    )
