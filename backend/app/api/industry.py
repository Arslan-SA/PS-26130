"""
Industry / MSME user role portal context and workspace endpoints.
Scoped strictly to the authenticated entrepreneur or industrialist.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_industry_user
from app.models.user import User

router = APIRouter(prefix="/industry", tags=["Industry User Portal"])


@router.get(
    "/dashboard-summary",
    summary="Get Industry Portal high-level operational overview",
)
async def get_industry_dashboard_summary(
    current_user: User = Depends(require_industry_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns summary metrics specifically scoped to the authenticated industry user.
    """
    return {
        "user_id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role.value,
        "workspace": {
            "has_completed_profile": False,
            "active_applications": 0,
            "pending_queries": 0,
            "upcoming_compliances": 0,
            "recommended_schemes": 0,
        },
        "next_action": "Complete Business Profile to run AI Approval Navigator.",
    }
