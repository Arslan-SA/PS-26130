"""
Business domain service managing enterprise onboarding, profile management, and validation.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, AuthorizationError
from app.models.business import Business
from app.models.business_profile import BusinessProfile
from app.models.user import User, UserRole
from app.schemas.business import (
    BusinessCreate,
    BusinessProfileCreate,
    BusinessProfileUpdate,
    BusinessUpdate,
    OnboardingRequest,
)


def calculate_profile_completeness(profile: BusinessProfile) -> int:
    """
    Compute percentage score (0-100) based on filled key operational attributes.
    """
    key_fields = [
        profile.nic_code,
        profile.manufacturing_activity,
        profile.products_services,
        profile.pollution_category,
        profile.state,
        profile.district,
        profile.pincode,
        profile.full_address,
        profile.total_employees,
        profile.plant_machinery_investment,
        profile.land_area_sqm,
        profile.annual_turnover,
        profile.power_requirement_kw,
        profile.water_requirement_kld,
        profile.contact_person,
        profile.contact_phone,
    ]
    completed_fields = sum(1 for val in key_fields if val is not None and str(val).strip() != "")
    score = int((completed_fields / len(key_fields)) * 100)
    return score


async def onboard_business(
    db: AsyncSession,
    user: User,
    request: OnboardingRequest,
) -> tuple[Business, list[str]]:
    """
    Orchestrate full enterprise onboarding: create legal Business and operational BusinessProfile.
    """
    pan_clean = request.business.pan.upper().strip()

    # 1. Ensure unique PAN
    existing_pan_stmt = select(Business).where(Business.pan == pan_clean)
    existing_pan = (await db.execute(existing_pan_stmt)).scalar_one_or_none()
    if existing_pan:
        raise ConflictError(
            message=f"An enterprise with PAN '{pan_clean}' is already registered.",
            details={"field": "pan", "value": pan_clean},
        )

    # 2. Ensure unique GSTIN if provided
    if request.business.gstin:
        gstin_clean = request.business.gstin.upper().strip()
        existing_gstin_stmt = select(Business).where(Business.gstin == gstin_clean)
        existing_gstin = (await db.execute(existing_gstin_stmt)).scalar_one_or_none()
        if existing_gstin:
            raise ConflictError(
                message=f"An enterprise with GSTIN '{gstin_clean}' is already registered.",
                details={"field": "gstin", "value": gstin_clean},
            )
    else:
        gstin_clean = None

    # 3. Create Business Entity
    business = Business(
        user_id=user.id,
        legal_name=request.business.legal_name.strip(),
        trade_name=request.business.trade_name.strip() if request.business.trade_name else None,
        entity_type=request.business.entity_type,
        pan=pan_clean,
        gstin=gstin_clean,
        udyam_number=request.business.udyam_number.strip() if request.business.udyam_number else None,
        cin=request.business.cin.strip() if request.business.cin else None,
        msme_category=request.business.msme_category,
        incorporation_date=request.business.incorporation_date,
        website=request.business.website.strip() if request.business.website else None,
        is_verified=False,
        is_active=True,
    )
    db.add(business)
    await db.flush()

    # 4. Create Operational Profile
    profile_data = request.profile.model_dump() if request.profile else {}
    profile = BusinessProfile(
        business_id=business.id,
        **profile_data,
    )
    completeness = calculate_profile_completeness(profile)
    profile.profile_completeness = completeness
    profile.is_profile_complete = (completeness >= 80)
    db.add(profile)
    await db.flush()

    await db.commit()
    await db.refresh(business)

    # Calculate dynamic onboarding next steps
    next_steps = []
    if not profile.is_profile_complete:
        next_steps.append("Complete operational profile (manufacturing details, workforce, power/water requirements)")
    if not business.gstin:
        next_steps.append("Add GSTIN identification for state single-window validation")
    if not profile.pollution_category:
        next_steps.append("Determine CPCB pollution category to identify required environmental NOCs")
    next_steps.append("Run AI Approval Discovery to generate personalized regulatory roadmap")

    return business, next_steps


async def get_business_by_id(
    db: AsyncSession,
    business_id: str,
    current_user: User,
) -> Business:
    """
    Retrieve business by ID with role-based ownership authorization.
    """
    stmt = (
        select(Business)
        .options(selectinload(Business.profile))
        .where(Business.id == business_id)
    )
    res = await db.execute(stmt)
    business = res.scalar_one_or_none()

    if not business:
        raise NotFoundError(
            message=f"Business with ID '{business_id}' not found.",
            details={"business_id": business_id},
        )

    # Check authorization: user must own business or be officer/admin
    if current_user.role == UserRole.INDUSTRY_USER and business.user_id != current_user.id:
        raise AuthorizationError(
            message="You do not have permission to access this business profile.",
            details={"business_id": business_id},
        )

    return business


async def get_user_businesses(
    db: AsyncSession,
    current_user: User,
) -> List[Business]:
    """
    Fetch all businesses associated with current user (or all if admin).
    """
    stmt = select(Business).options(selectinload(Business.profile))
    if current_user.role == UserRole.INDUSTRY_USER:
        stmt = stmt.where(Business.user_id == current_user.id)

    res = await db.execute(stmt)
    return list(res.scalars().all())


async def update_business(
    db: AsyncSession,
    business_id: str,
    update_data: BusinessUpdate,
    current_user: User,
) -> Business:
    """
    Update core legal business attributes.
    """
    business = await get_business_by_id(db, business_id, current_user)

    for field, val in update_data.model_dump(exclude_unset=True).items():
        if val is not None:
            if field in ("pan", "gstin"):
                val = val.upper().strip()
            elif isinstance(val, str):
                val = val.strip()
        setattr(business, field, val)

    await db.commit()
    await db.refresh(business)
    return business


async def update_business_profile(
    db: AsyncSession,
    business_id: str,
    update_data: BusinessProfileUpdate,
    current_user: User,
) -> BusinessProfile:
    """
    Update operational industrial profile and recalculate completeness.
    """
    business = await get_business_by_id(db, business_id, current_user)
    profile = business.profile

    if not profile:
        profile = BusinessProfile(business_id=business.id)
        db.add(profile)
        await db.flush()

    for field, val in update_data.model_dump(exclude_unset=True).items():
        setattr(profile, field, val)

    completeness = calculate_profile_completeness(profile)
    profile.profile_completeness = completeness
    profile.is_profile_complete = (completeness >= 80)

    await db.commit()
    await db.refresh(profile)
    return profile
