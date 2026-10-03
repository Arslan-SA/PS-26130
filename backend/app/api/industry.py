"""
Industry / MSME user role portal context and workspace endpoints.
Scoped strictly to the authenticated entrepreneur or industrialist.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import require_industry_user
from app.models.application import Application
from app.models.business import Business
from app.models.compliance import ComplianceRecord, ComplianceRecordStatus
from app.models.scheme import GovernmentScheme
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
    stmt_biz = (
        select(Business)
        .options(selectinload(Business.profile))
        .where(Business.user_id == current_user.id)
        .limit(1)
    )
    res_biz = await db.execute(stmt_biz)
    business = res_biz.scalar_one_or_none()

    has_completed_profile = bool(business and business.profile and business.profile.is_profile_complete)
    active_apps_count = 0
    upcoming_compliances_count = 0
    recommended_schemes_count = 0

    if business:
        # Active statutory applications
        stmt_apps = select(func.count(Application.id)).where(Application.business_id == business.id)
        res_apps = await db.execute(stmt_apps)
        active_apps_count = res_apps.scalar() or 0

        # Upcoming compliance records
        stmt_comp = select(func.count(ComplianceRecord.id)).where(
            ComplianceRecord.business_id == business.id,
            ComplianceRecord.status.in_([ComplianceRecordStatus.UPCOMING, ComplianceRecordStatus.DUE_SOON]),
        )
        res_comp = await db.execute(stmt_comp)
        upcoming_compliances_count = res_comp.scalar() or 0

        # Active schemes in catalog
        stmt_sch = select(func.count(GovernmentScheme.id)).where(GovernmentScheme.is_active == True)
        res_sch = await db.execute(stmt_sch)
        recommended_schemes_count = res_sch.scalar() or 0

    next_action = "Explore available Government Schemes & Subsidies." if has_completed_profile else "Complete Business Profile to run AI Approval Navigator."

    return {
        "user_id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role.value,
        "workspace": {
            "has_completed_profile": has_completed_profile,
            "active_applications": active_apps_count,
            "pending_queries": 0,
            "upcoming_compliances": upcoming_compliances_count,
            "recommended_schemes": recommended_schemes_count,
        },
        "next_action": next_action,
    }

