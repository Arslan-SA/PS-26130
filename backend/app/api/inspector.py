"""
Field Inspector portal context and site inspection workspace endpoints.
Scoped strictly to physical plant site visits assigned to the inspector.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_inspector
from app.models.user import User

router = APIRouter(prefix="/inspector", tags=["Field Inspector Portal"])


@router.get(
    "/schedule-summary",
    summary="Get Inspector site visit schedule and report summary",
)
async def get_inspector_schedule_summary(
    current_user: User = Depends(require_inspector),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns physical inspection visit metrics assigned to the authenticated inspector.
    """
    return {
        "inspector_id": current_user.id,
        "full_name": current_user.full_name,
        "department_id": current_user.department_id or "DISH_INSPECTORATE",
        "designation": current_user.designation or "Senior Industrial Safety Inspector",
        "role": current_user.role.value,
        "inspection_metrics": {
            "assigned_site_visits_pending": 0,
            "reports_pending_submission": 0,
            "completed_inspections": 0,
            "non_compliance_flags_raised": 0,
        },
        "next_action": "Conduct site inspection visit for assigned industrial unit.",
    }
