"""
Field Inspector portal context and site inspection workspace endpoints (Fragments 87, 88).
Scoped strictly to physical plant site visits assigned to the inspector.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import require_inspector
from app.models.inspection import Inspection, InspectionStatus
from app.models.user import User
from app.schemas.application import InspectionRead, InspectionReportPayload
from app.services.application_service import ApplicationWorkflowService

router = APIRouter(prefix="/inspector", tags=["Field Inspector Portal"])


@router.get(
    "/schedule-summary",
    summary="Get Inspector site visit schedule and report summary",
)
async def get_inspector_schedule_summary(
    current_user: User = Depends(require_inspector),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Returns physical inspection visit metrics assigned to the authenticated inspector (Fragment 87)."""
    stmt = select(Inspection).where(Inspection.inspector_id == current_user.id)
    inspections = (await db.execute(stmt)).scalars().all()

    pending_visits = sum(1 for i in inspections if i.status == InspectionStatus.SCHEDULED)
    in_progress = sum(1 for i in inspections if i.status == InspectionStatus.IN_PROGRESS)
    completed = sum(1 for i in inspections if i.status == InspectionStatus.COMPLETED)
    non_compliant = sum(
        1 for i in inspections
        if i.recommendation and i.recommendation.value in ("NON_COMPLIANT", "REMEDIATION_REQUIRED")
    )

    next_action = "Conduct site inspection visit for assigned industrial unit."
    if pending_visits > 0:
        next_action = f"{pending_visits} physical plant inspections scheduled on your calendar."
    elif completed > 0:
        next_action = "All assigned inspections up-to-date."

    return {
        "inspector_id": current_user.id,
        "full_name": current_user.full_name,
        "department_id": current_user.department_id or "DISH_INSPECTORATE",
        "designation": current_user.designation or "Senior Industrial Safety Inspector",
        "role": current_user.role.value,
        "inspection_metrics": {
            "assigned_site_visits_pending": pending_visits,
            "in_progress": in_progress,
            "completed_inspections": completed,
            "non_compliance_flags_raised": non_compliant,
        },
        "next_action": next_action,
    }


@router.get(
    "/schedule",
    response_model=List[InspectionRead],
    summary="List all site visits assigned to current inspector",
)
async def list_assigned_inspections(
    current_user: User = Depends(require_inspector),
    db: AsyncSession = Depends(get_db),
) -> List[InspectionRead]:
    """Returns all inspections assigned to current inspector (Fragment 87)."""
    stmt = (
        select(Inspection)
        .where(Inspection.inspector_id == current_user.id)
        .options(selectinload(Inspection.inspector))
        .order_by(Inspection.scheduled_date.asc())
    )
    inspections = (await db.execute(stmt)).scalars().all()

    return [
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
        for i in inspections
    ]


@router.post(
    "/inspections/{id}/report",
    response_model=InspectionRead,
    summary="Submit field inspection verification findings and report",
)
async def submit_inspection_report(
    id: str,
    payload: InspectionReportPayload,
    current_user: User = Depends(require_inspector),
    db: AsyncSession = Depends(get_db),
) -> InspectionRead:
    """Inspector submits physical observations, checklist, geolocated coords and recommendation (Fragment 88)."""
    insp = await ApplicationWorkflowService.submit_inspection_report(db, id, payload, current_user)
    return InspectionRead(
        id=insp.id,
        application_id=insp.application_id,
        inspector_id=insp.inspector_id,
        inspector_name=current_user.full_name,
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
