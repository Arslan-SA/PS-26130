"""
REST API endpoints for statutory approval discovery, requirement tracking, and clearance summaries.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import AuthorizationError, NotFoundError
from app.models.approval import Approval
from app.models.approval_requirement import ApprovalRequirement, RequirementStatus
from app.models.business import Business
from app.models.user import User, UserRole
from app.schemas.approval import (
    ApprovalChecklistRead,
    ApprovalRequirementRead,
    ChecklistItemRead,
    ClearanceSummaryRead,
    DiscoveryResponse,
)
from app.services.approval_checklist import get_approval_checklist
from app.services.requirement_engine import RequirementEngineService

router = APIRouter(prefix="/approvals", tags=["Approvals & Clearances"])


class StatusUpdatePayload(BaseModel):
    """Payload to update an approval requirement status."""
    status: RequirementStatus
    notes: str | None = None


async def _verify_business_access(business_id: str, current_user: User, db: AsyncSession) -> Business:
    """Ensure business exists and requesting user is authorized (owner or gov official)."""
    stmt = select(Business).where(Business.id == business_id)
    business = (await db.execute(stmt)).scalar_one_or_none()
    if not business:
        raise NotFoundError("Business not found", details={"business_id": business_id})

    # Industry users can only inspect their own businesses
    if current_user.role == UserRole.INDUSTRY_USER and business.user_id != current_user.id:
        raise AuthorizationError("You do not have permission to view or manage this business unit.")

    return business


@router.post("/discover/{business_id}", response_model=DiscoveryResponse, status_code=status.HTTP_200_OK)
async def discover_approvals(
    business_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiscoveryResponse:
    """
    Execute statutory requirement discovery engine for an enterprise.
    Identifies mandatory and conditional clearances, calculates statutory fees,
    reconciles database records, and returns consolidated compliance metrics.
    """
    await _verify_business_access(business_id, current_user, db)

    requirements = await RequirementEngineService.generate_requirements_for_business(db, business_id)
    summary_data = await RequirementEngineService.get_business_clearance_summary(db, business_id)

    return DiscoveryResponse(
        business_id=business_id,
        count=len(requirements),
        requirements=[ApprovalRequirementRead.model_validate(r) for r in requirements],
        summary=ClearanceSummaryRead(**summary_data),
    )


@router.get("/business/{business_id}", response_model=List[ApprovalRequirementRead])
async def list_business_requirements(
    business_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ApprovalRequirementRead]:
    """Retrieve all identified approval requirements for an industrial enterprise."""
    await _verify_business_access(business_id, current_user, db)

    stmt = (
        select(ApprovalRequirement)
        .where(ApprovalRequirement.business_id == business_id)
        .order_by(ApprovalRequirement.priority.asc(), ApprovalRequirement.created_at.asc())
    )
    reqs = (await db.execute(stmt)).scalars().all()
    return [ApprovalRequirementRead.model_validate(r) for r in reqs]


@router.get("/summary/{business_id}", response_model=ClearanceSummaryRead)
async def get_clearance_summary(
    business_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClearanceSummaryRead:
    """Retrieve consolidated clearance summary metrics, fee totals, and critical path days."""
    await _verify_business_access(business_id, current_user, db)
    summary_data = await RequirementEngineService.get_business_clearance_summary(db, business_id)
    return ClearanceSummaryRead(**summary_data)


@router.patch("/requirements/{requirement_id}/status", response_model=ApprovalRequirementRead)
async def update_requirement_status(
    requirement_id: str,
    payload: StatusUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalRequirementRead:
    """Update requirement compliance lifecycle status and notes."""
    stmt = select(ApprovalRequirement).where(ApprovalRequirement.id == requirement_id)
    req = (await db.execute(stmt)).scalar_one_or_none()
    if not req:
        raise NotFoundError("Approval requirement not found", details={"requirement_id": requirement_id})

    await _verify_business_access(req.business_id, current_user, db)

    req.status = payload.status
    if payload.notes is not None:
        req.notes = payload.notes

    await db.commit()
    await db.refresh(req)
    return ApprovalRequirementRead.model_validate(req)


@router.get("/{approval_code}/checklist", response_model=ApprovalChecklistRead)
async def get_checklist_by_code(
    approval_code: str,
    current_user: User = Depends(get_current_user),
) -> ApprovalChecklistRead:
    """Retrieve the statutory checklist for an approval code."""
    checklist = get_approval_checklist(approval_code.upper())
    if not checklist:
        raise NotFoundError("Checklist not found for this clearance code", details={"code": approval_code})
    return ApprovalChecklistRead(
        approval_code=checklist.approval_code,
        approval_title=checklist.approval_title,
        issuing_authority=checklist.issuing_authority,
        statutory_act=checklist.statutory_act,
        items=[ChecklistItemRead(**item.__dict__) for item in checklist.items],
    )


@router.get("/requirements/{requirement_id}/checklist", response_model=ApprovalChecklistRead)
async def get_checklist_for_requirement(
    requirement_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalChecklistRead:
    """Retrieve statutory checklist customized for a specific requirement instance."""
    stmt = (
        select(ApprovalRequirement, Approval)
        .join(Approval, ApprovalRequirement.approval_id == Approval.id)
        .where(ApprovalRequirement.id == requirement_id)
    )
    res = (await db.execute(stmt)).first()
    if not res:
        raise NotFoundError("Requirement not found", details={"requirement_id": requirement_id})
    req, approval = res
    await _verify_business_access(req.business_id, current_user, db)

    checklist = get_approval_checklist(approval.code)
    if not checklist:
        raise NotFoundError("Checklist not found for clearance code", details={"code": approval.code})

    return ApprovalChecklistRead(
        approval_code=checklist.approval_code,
        approval_title=checklist.approval_title,
        issuing_authority=checklist.issuing_authority,
        statutory_act=checklist.statutory_act,
        items=[ChecklistItemRead(**item.__dict__) for item in checklist.items],
    )

