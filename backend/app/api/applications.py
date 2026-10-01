"""
Statutory Clearance Application API Endpoints (Fragments 77, 78, 80, 84, 85).
Provides applicant portal with creation, submission, tracking, query resolution, and resubmission.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.application import ApplicationStatus
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetailRead,
    ApplicationListResponse,
    ApplicationQueryRead,
    ApplicationQueryRespondPayload,
    ApplicationSubmitPayload,
    ApplicationSummaryRead,
    ApplicationUpdate,
)
from app.services.application_service import ApplicationWorkflowService

router = APIRouter(prefix="/applications", tags=["Applications & Submissions"])


@router.post("/", response_model=ApplicationDetailRead, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetailRead:
    """Create a new draft application for a statutory clearance (Fragment 77)."""
    app_entity = await ApplicationWorkflowService.create_application(db, payload, current_user)
    return await ApplicationWorkflowService.get_application_detail(db, app_entity.id, current_user)


@router.get("/", response_model=List[ApplicationSummaryRead], status_code=status.HTTP_200_OK)
async def list_applications(
    business_id: Optional[str] = Query(None, description="Filter by business ID"),
    department_code: Optional[str] = Query(None, description="Filter by department code"),
    status: Optional[ApplicationStatus] = Query(None, description="Filter by application status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ApplicationSummaryRead]:
    """List applications accessible to current user with optional filtering (Fragment 80)."""
    return await ApplicationWorkflowService.list_applications(
        db,
        current_user=current_user,
        business_id=business_id,
        department_code=department_code,
        status=status,
    )


@router.get("/{id}", response_model=ApplicationDetailRead, status_code=status.HTTP_200_OK)
async def get_application_detail(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetailRead:
    """Retrieve full application detail with history, deficiency queries, and inspections (Fragment 80)."""
    return await ApplicationWorkflowService.get_application_detail(db, id, current_user)


@router.post("/{id}/submit", response_model=ApplicationDetailRead, status_code=status.HTTP_200_OK)
async def submit_application(
    id: str,
    payload: ApplicationSubmitPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetailRead:
    """Formally submit a draft application with fee verification (Fragment 78)."""
    await ApplicationWorkflowService.submit_application(db, id, payload, current_user)
    return await ApplicationWorkflowService.get_application_detail(db, id, current_user)


@router.post("/{id}/queries/{query_id}/respond", response_model=ApplicationQueryRead, status_code=status.HTTP_200_OK)
async def respond_to_query(
    id: str,
    query_id: str,
    payload: ApplicationQueryRespondPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationQueryRead:
    """Applicant responds to a deficiency note with clarification or replacement doc (Fragment 84)."""
    query = await ApplicationWorkflowService.respond_to_query(db, id, query_id, payload, current_user)
    return ApplicationQueryRead(
        id=query.id,
        application_id=query.application_id,
        raised_by_user_id=query.raised_by_user_id,
        raised_by_name=query.raised_by.full_name if query.raised_by else None,
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


@router.post("/{id}/resubmit", response_model=ApplicationDetailRead, status_code=status.HTTP_200_OK)
async def resubmit_application(
    id: str,
    remarks: Optional[str] = Query(None, description="Optional resubmission summary remarks"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetailRead:
    """Applicant resubmits application after resolving all open deficiency queries (Fragment 85)."""
    await ApplicationWorkflowService.resubmit_application(db, id, remarks, current_user)
    return await ApplicationWorkflowService.get_application_detail(db, id, current_user)
