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
from app.models.approval_dependency import ApprovalDependency, DependencyType
from app.models.business import Business
from app.models.user import User, UserRole
from app.schemas.approval import (
    ApprovalChecklistRead,
    ApprovalRequirementRead,
    ChecklistItemRead,
    ClearanceSummaryRead,
    DependencyGraphResponse,
    DiscoveryResponse,
    GraphEdge,
    GraphNode,
    RoadmapActivityRead,
    RoadmapMilestoneRead,
    RoadmapPlanResponse,
)
from app.services.approval_checklist import get_approval_checklist
from app.services.dependency_engine import DependencyEngineService
from app.services.requirement_engine import RequirementEngineService
from app.services.roadmap_service import RoadmapService

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


@router.get("/requirements/{requirement_id}", response_model=ApprovalRequirementRead)
async def get_requirement_by_id(
    requirement_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalRequirementRead:
    """Retrieve requirement details with parent approval metadata."""
    stmt = select(ApprovalRequirement).where(ApprovalRequirement.id == requirement_id)
    req = (await db.execute(stmt)).scalar_one_or_none()
    if not req:
        raise NotFoundError("Approval requirement not found", details={"requirement_id": requirement_id})

    await _verify_business_access(req.business_id, current_user, db)
    return ApprovalRequirementRead.model_validate(req)


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


@router.get("/graph/{business_id}", response_model=DependencyGraphResponse)
async def get_approval_dependency_graph(
    business_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DependencyGraphResponse:
    """
    Generate the complete statutory clearance Directed Acyclic Graph (DAG) for an enterprise.
    Returns nodes with real-time unlock/blocking status, prerequisite edges, topological order,
    and critical turnaround path calculations.
    """
    await _verify_business_access(business_id, current_user, db)

    # 1. Fetch requirements and parent approvals
    stmt = (
        select(ApprovalRequirement, Approval)
        .join(Approval, ApprovalRequirement.approval_id == Approval.id)
        .where(ApprovalRequirement.business_id == business_id)
    )
    rows = (await db.execute(stmt)).all()

    # If empty, run discovery once automatically
    if not rows:
        await RequirementEngineService.generate_requirements_for_business(db, business_id)
        rows = (await db.execute(stmt)).all()

    active_rows = [
        (req, app) for req, app in rows if req.status != RequirementStatus.EXEMPTED
    ]

    code_by_approval_id = {app.id: app.code for _, app in active_rows}
    active_codes = set(code_by_approval_id.values())
    sla_by_code = {app.code: req.sla_deadline_days for req, app in active_rows}

    # 2. Evaluate real-time prerequisite unlock states
    reqs = [r for r, _ in active_rows]
    unlock_map = await DependencyEngineService.evaluate_requirement_unlocks(
        db, reqs, code_by_approval_id
    )

    # 3. Fetch dependencies and filter edges between active nodes
    dep_stmt = select(ApprovalDependency)
    dependencies = (await db.execute(dep_stmt)).scalars().all()

    edges: List[GraphEdge] = []
    dag_edges: List[tuple[str, str]] = []

    for d in dependencies:
        if d.from_approval_code in active_codes and d.to_approval_code in active_codes:
            edges.append(
                GraphEdge(
                    id=f"{d.from_approval_code}->{d.to_approval_code}",
                    source=d.from_approval_code,
                    target=d.to_approval_code,
                    dependency_type=d.dependency_type.value,
                    description=d.description,
                )
            )
            if d.dependency_type == DependencyType.MANDATORY_PREREQUISITE:
                dag_edges.append((d.from_approval_code, d.to_approval_code))

    # 4. Topological order and critical path
    node_codes = list(active_codes)
    topological_order = DependencyEngineService.topological_sort(node_codes, dag_edges)
    critical_days, critical_path = DependencyEngineService.calculate_critical_path(
        node_codes, dag_edges, sla_by_code
    )

    # 5. Build GraphNode objects
    nodes: List[GraphNode] = []
    for req, app in active_rows:
        unlock_info = unlock_map.get(app.code)
        nodes.append(
            GraphNode(
                id=app.code,
                requirement_id=req.id,
                title=app.title,
                department_code=app.department_code,
                issuing_authority=app.issuing_authority,
                stage=req.stage,
                status=req.status,
                is_unlocked=unlock_info.is_unlocked if unlock_info else True,
                missing_prerequisites=unlock_info.missing_prerequisites if unlock_info else [],
                estimated_fee=req.estimated_fee,
                sla_days=req.sla_deadline_days,
                priority=req.priority,
            )
        )

    return DependencyGraphResponse(
        business_id=business_id,
        nodes=nodes,
        edges=edges,
        topological_order=topological_order,
        critical_path=critical_path,
        critical_path_days=critical_days,
    )


@router.get("/roadmap/{business_id}", response_model=RoadmapPlanResponse)
async def get_clearance_roadmap(
    business_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoadmapPlanResponse:
    """Retrieve personalized statutory clearance timeline and milestone schedule."""
    await _verify_business_access(business_id, current_user, db)
    plan = await RoadmapService.generate_roadmap(db, business_id)
    return RoadmapPlanResponse(
        business_id=plan.business_id,
        base_start_date=plan.base_start_date.isoformat(),
        projected_commissioning_date=plan.projected_commissioning_date.isoformat(),
        total_calendar_days=plan.total_calendar_days,
        critical_path_days=plan.critical_path_days,
        activities=[
            RoadmapActivityRead(
                approval_code=a.approval_code,
                requirement_id=a.requirement_id,
                title=a.title,
                department_code=a.department_code,
                stage=a.stage,
                status=a.status,
                sla_days=a.sla_days,
                estimated_fee=a.estimated_fee,
                start_day_offset=a.start_day_offset,
                finish_day_offset=a.finish_day_offset,
                scheduled_start=a.scheduled_start.isoformat(),
                scheduled_finish=a.scheduled_finish.isoformat(),
                is_critical=a.is_critical,
                prerequisites=a.prerequisites,
            )
            for a in plan.activities
        ],
        milestones=[
            RoadmapMilestoneRead(
                phase_id=m.phase_id,
                title=m.title,
                description=m.description,
                start_day=m.start_day,
                finish_day=m.finish_day,
                scheduled_start=m.scheduled_start.isoformat(),
                scheduled_finish=m.scheduled_finish.isoformat(),
                activity_count=m.activity_count,
                total_estimated_fee=m.total_estimated_fee,
            )
            for m in plan.milestones
        ],
    )



