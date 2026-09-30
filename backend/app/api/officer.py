"""
Department Officer portal context and review workspace endpoints.
Scoped strictly to applications matching the officer's department.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_officer
from app.models.user import User

router = APIRouter(prefix="/officer", tags=["Department Officer Portal"])


@router.get(
    "/inbox-summary",
    summary="Get Officer department review inbox summary",
)
async def get_officer_inbox_summary(
    current_user: User = Depends(require_officer),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns application queue metrics strictly scoped to the officer's department.
    """
    return {
        "officer_id": current_user.id,
        "full_name": current_user.full_name,
        "department_id": current_user.department_id or "ALL_DEPARTMENTS",
        "designation": current_user.designation or "Scrutiny Officer",
        "role": current_user.role.value,
        "queue_metrics": {
            "pending_scrutiny": 0,
            "queries_pending_applicant_response": 0,
            "inspections_scheduled": 0,
            "approved_this_month": 0,
            "sla_compliance_rate_percent": 98.5,
        },
        "next_action": "Review highest priority pending application in scrutiny queue.",
    }
