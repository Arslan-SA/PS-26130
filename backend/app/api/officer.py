"""
Department Officer portal context and review workspace endpoints (Fragments 81, 82, 83, 87, 89).
Scoped strictly to applications matching the officer's department.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_officer
from app.models.application import ApplicationStatus
from app.models.user import User
from app.schemas.application import (
    ApplicationDetailRead,
    ApplicationQueryCreate,
    ApplicationQueryRead,
    ApplicationSummaryRead,
    InspectionRead,
    InspectionSchedulePayload,
    OfficerInboxSummaryResponse,
    StatutoryDeterminationPayload,
)
from app.services.application_service import ApplicationWorkflowService

router = APIRouter(prefix="/officer", tags=["Department Officer Portal"])


@router.get(
    "/inbox-summary",
    response_model=OfficerInboxSummaryResponse,
    summary="Get Officer department review inbox summary with real metrics",
)
async def get_officer_inbox_summary(
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db),
) -> OfficerInboxSummaryResponse:
    """Returns application queue metrics strictly scoped to the officer's department (Fragment 81)."""
    return await ApplicationWorkflowService.get_officer_inbox_metrics(db, current_user)


@router.get(
    "/applications",
    response_model=List[ApplicationSummaryRead],
    summary="List applications in officer department queue",
)
async def list_officer_applications(
    status: Optional[ApplicationStatus] = Query(None, description="Filter by status"),
    department_code: Optional[str] = Query(None, description="Optional override department code"),
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db),
) -> List[ApplicationSummaryRead]:
    """Returns departmental scrutiny queue for current officer (Fragment 81)."""
    return await ApplicationWorkflowService.list_applications(
        db,
        current_user=current_user,
        department_code=department_code,
        status=status,
    )


@router.post(
    "/applications/{id}/review",
    response_model=ApplicationDetailRead,
    summary="Commence formal statutory scrutiny on application",
)
async def start_officer_review(
    id: str,
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetailRead:
    """Assigns current officer and marks application UNDER_REVIEW (Fragment 82)."""
    await ApplicationWorkflowService.start_review(db, id, current_user)
    return await ApplicationWorkflowService.get_application_detail(db, id, current_user)


@router.post(
    "/applications/{id}/queries",
    response_model=ApplicationQueryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Raise formal deficiency query / document clarification",
)
async def raise_deficiency_query(
    id: str,
    payload: ApplicationQueryCreate,
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db),
) -> ApplicationQueryRead:
    """Officer flags document/form deficiency and requests applicant rectification (Fragment 83)."""
    query = await ApplicationWorkflowService.raise_deficiency_query(db, id, payload, current_user)
    return ApplicationQueryRead(
        id=query.id,
        application_id=query.application_id,
        raised_by_user_id=query.raised_by_user_id,
        raised_by_name=current_user.full_name,
        document_id=query.document_id,
        query_title=query.query_title,
        query_text=query.query_text,
        status=query.status,
        due_date=query.due_date,
        response_text=query.response_text,
        response_document_id=query.response_document_id,
        resolved_at=query.resolved_at,
        created_at=query.created_at,
    )


@router.post(
    "/applications/{id}/schedule-inspection",
    response_model=InspectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule physical plant site inspection and assign inspector",
)
async def schedule_inspection(
    id: str,
    payload: InspectionSchedulePayload,
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db),
) -> InspectionRead:
    """Appoints field inspector and sets physical visit date (Fragment 87)."""
    insp = await ApplicationWorkflowService.schedule_inspection(db, id, payload, current_user)
    return InspectionRead(
        id=insp.id,
        application_id=insp.application_id,
        inspector_id=insp.inspector_id,
        inspector_name=insp.inspector.full_name if insp.inspector else None,
        department_id=insp.department_id,
        scheduled_date=insp.scheduled_date,
        status=insp.status,
        instructions=insp.instructions,
        findings=insp.findings,
        checklist_results=insp.checklist_results or {},
        recommendation=insp.recommendation,
        geo_latitude=insp.geo_latitude,
        geo_longitude=insp.geo_longitude,
        report_document_id=insp.report_document_id,
        completed_at=insp.completed_at,
        created_at=insp.created_at,
    )


@router.post(
    "/applications/{id}/determine",
    response_model=ApplicationDetailRead,
    summary="Render final statutory decision (Approve or Reject)",
)
async def determine_application(
    id: str,
    payload: StatutoryDeterminationPayload,
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetailRead:
    """Final regulatory clearance determination: approves with certificate or rejects with legal reason (Fragment 89)."""
    await ApplicationWorkflowService.determine_application(db, id, payload, current_user)
    return await ApplicationWorkflowService.get_application_detail(db, id, current_user)
