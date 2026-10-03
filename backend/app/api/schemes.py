"""
Government Schemes & Subsidies REST API endpoints (Phase 8, Fragment 107).

Provides:
- Scheme catalog discovery and filtering
- Business-tailored AI/Rule eligibility recommendations
- In-depth criterion evaluation & Document Vault gap analysis
- Scheme application tracking & bookmarking
- Admin catalog seeding
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin, require_industry_user
from app.models.business import Business
from app.models.scheme import (
    GovernmentScheme,
    SchemeApplication,
    SchemeApplicationStatus,
    SchemeLevel,
    SchemeType,
)
from app.models.user import User
from app.services import scheme_service

router = APIRouter(prefix="/schemes", tags=["Government Schemes & Incentives"])


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class SchemeApplicationCreate(BaseModel):
    business_id: str
    scheme_id: str
    status: Optional[str] = "BOOKMARKED"
    notes: Optional[str] = None
    application_reference_number: Optional[str] = None


class SchemeApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    sanctioned_amount: Optional[float] = None
    application_reference_number: Optional[str] = None


# ---------------------------------------------------------------------------
# Admin Endpoints
# ---------------------------------------------------------------------------

@router.post("/admin/seed", summary="Seed Government Schemes Catalog")
async def seed_schemes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Dict[str, Any]:
    """Seed or update initial Central & State schemes and eligibility rules."""
    count = await scheme_service.seed_government_schemes(db)
    return {"message": f"Successfully seeded {count} government incentive schemes.", "count": count}


# ---------------------------------------------------------------------------
# Catalog Endpoints (Discovery)
# ---------------------------------------------------------------------------

@router.get("/catalog", summary="List Scheme Catalog")
async def list_scheme_catalog(
    scheme_type: Optional[SchemeType] = Query(None, description="Filter by scheme incentive type"),
    level: Optional[SchemeLevel] = Query(None, description="Filter by Central or State level"),
    search: Optional[str] = Query(None, description="Search term for name or tags"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Lists all available government incentive and subsidy schemes."""
    stmt = (
        select(GovernmentScheme)
        .options(selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.is_active == True)
    )

    if scheme_type:
        stmt = stmt.where(GovernmentScheme.scheme_type == scheme_type)
    if level:
        stmt = stmt.where(GovernmentScheme.level == level)

    result = await db.execute(stmt)
    schemes = result.scalars().all()

    output = []
    for s in schemes:
        if search:
            q = search.lower()
            in_name = q in s.name.lower() or q in s.short_name.lower()
            in_ministry = q in s.ministry.lower()
            in_tags = any(q in t.lower() for t in s.tags)
            if not (in_name or in_ministry or in_tags):
                continue
        output.append(s.to_dict())

    return output


@router.get("/{scheme_id}", summary="Get Scheme Details")
async def get_scheme_details(
    scheme_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieves complete scheme details, eligibility rule parameters, and guidance steps."""
    stmt = (
        select(GovernmentScheme)
        .options(selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.id == scheme_id)
    )
    res = await db.execute(stmt)
    scheme = res.scalar_one_or_none()
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Government scheme with ID {scheme_id} not found.",
        )
    return scheme.to_dict()


# ---------------------------------------------------------------------------
# Business Matching & Recommendation Endpoints (Fragments 106, 108, 109, 110)
# ---------------------------------------------------------------------------

@router.get("/recommendations/{business_id}", summary="Get Matched Schemes for Business")
async def get_business_scheme_recommendations(
    business_id: str,
    scheme_type: Optional[str] = None,
    min_score: float = Query(0.0, ge=0.0, le=100.0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Runs the deterministic eligibility engine against the business's profile.
    Ranks schemes by eligibility, match percentage, and maximum subsidy potential.
    """
    # Verify business existence & access
    stmt = select(Business).where(Business.id == business_id)
    res = await db.execute(stmt)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found.",
        )

    # Scoped authorization
    if current_user.role.value == "INDUSTRY_USER" and business.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to access this enterprise's scheme recommendations.",
        )

    # Ensure catalog has been seeded at least once
    stmt_check = select(GovernmentScheme).limit(1)
    res_check = await db.execute(stmt_check)
    if not res_check.scalar_one_or_none():
        await scheme_service.seed_government_schemes(db)

    recommendations = await scheme_service.get_recommended_schemes_for_business(
        db=db,
        business_id=business_id,
        scheme_type_filter=scheme_type,
        min_score=min_score,
    )

    # Calculate summary metrics
    total_eligible = sum(1 for r in recommendations if r["is_eligible"])
    total_subsidy_potential = sum(
        r["estimated_subsidy_amount"] or 0.0 for r in recommendations if r["is_eligible"]
    )

    return {
        "business_id": business_id,
        "total_schemes_evaluated": len(recommendations),
        "total_eligible_schemes": total_eligible,
        "total_subsidy_potential_inr": round(total_subsidy_potential, 2),
        "schemes": recommendations,
    }


@router.get("/{scheme_id}/evaluate/{business_id}", summary="Detailed Evaluation & Gap Analysis")
async def evaluate_single_scheme_for_business(
    scheme_id: str,
    business_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Performs full criterion audit and Document Vault readiness gap analysis
    for a single business and specific scheme.
    """
    stmt = (
        select(GovernmentScheme)
        .options(selectinload(GovernmentScheme.rule))
        .where(GovernmentScheme.id == scheme_id)
    )
    res = await db.execute(stmt)
    scheme = res.scalar_one_or_none()
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheme not found.",
        )

    stmt_biz = (
        select(Business)
        .options(selectinload(Business.profile))
        .where(Business.id == business_id)
    )
    res_biz = await db.execute(stmt_biz)
    business = res_biz.scalar_one_or_none()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found.",
        )

    if current_user.role.value == "INDUSTRY_USER" and business.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to evaluate this business.",
        )

    # 1. Eligibility evaluation
    evaluation = scheme_service.evaluate_scheme_eligibility(scheme, business, business.profile)

    # 2. Document gap analysis (Fragment 110)
    doc_gap = await scheme_service.analyze_scheme_document_gaps(db, scheme, business.id)

    return {
        **evaluation,
        "document_readiness": doc_gap,
    }


# ---------------------------------------------------------------------------
# Scheme Application & Bookmark Management Endpoints (Fragment 111)
# ---------------------------------------------------------------------------

@router.post("/applications", summary="Bookmark or Track Scheme Application")
async def track_scheme_application(
    payload: SchemeApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_industry_user),
) -> Dict[str, Any]:
    """Bookmark a recommended scheme or record active application status."""
    try:
        status_enum = SchemeApplicationStatus(payload.status or "BOOKMARKED")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{payload.status}'.",
        )

    try:
        app_record = await scheme_service.bookmark_or_apply_scheme(
            db=db,
            business_id=payload.business_id,
            scheme_id=payload.scheme_id,
            status=status_enum,
            notes=payload.notes,
            application_reference_number=payload.application_reference_number,
        )
        return app_record.to_dict()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/applications/{business_id}", summary="List Business Scheme Applications")
async def list_business_applications(
    business_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List all scheme bookmarks, preparations, and applications for an enterprise."""
    applications = await scheme_service.get_business_scheme_applications(db, business_id)
    return [a.to_dict() for a in applications]


@router.patch("/applications/{application_id}", summary="Update Application Milestone")
async def update_scheme_application(
    application_id: str,
    payload: SchemeApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update application status, reference number, notes, or sanctioned amount."""
    stmt = (
        select(SchemeApplication)
        .options(selectinload(SchemeApplication.scheme))
        .where(SchemeApplication.id == application_id)
    )
    res = await db.execute(stmt)
    app_record = res.scalar_one_or_none()
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheme application record not found.",
        )

    if payload.status:
        try:
            app_record.status = SchemeApplicationStatus(payload.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{payload.status}'.",
            )
    if payload.notes is not None:
        app_record.notes = payload.notes
    if payload.application_reference_number is not None:
        app_record.application_reference_number = payload.application_reference_number
    if payload.sanctioned_amount is not None:
        app_record.sanctioned_amount = payload.sanctioned_amount

    await db.commit()
    await db.refresh(app_record)
    return app_record.to_dict()
