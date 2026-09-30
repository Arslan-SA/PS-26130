"""
REST API endpoints for Business Onboarding, Industrial Profiles, and Completeness Evaluation.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.business import (
    BusinessProfileResponse,
    BusinessProfileUpdate,
    BusinessResponse,
    BusinessUpdate,
    OnboardingRequest,
    OnboardingResponse,
)
from app.services.business_service import (
    get_business_by_id,
    get_user_businesses,
    onboard_business,
    update_business,
    update_business_profile,
)
from app.services.classification_service import classify_industry
from app.services.completeness_service import evaluate_profile_completeness
from app.services.location_service import validate_pincode
from app.services.validation_service import (
    validate_cin,
    validate_gstin,
    validate_pan,
    validate_udyam_number,
)

router = APIRouter(prefix="/business", tags=["Business & Industrial Profile"])


@router.post("/onboard", response_model=OnboardingResponse, status_code=status.HTTP_201_CREATED)
async def onboard_enterprise(
    request: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingResponse:
    """
    Onboard an industrial enterprise:
    - Validates PAN, GSTIN, CIN, and Udyam statutory formats
    - Validates postal pincode
    - Automatically classifies CPCB category if not manually provided
    - Persists Business and BusinessProfile records
    """
    # 1. Statutory Validation
    validate_pan(request.business.pan, request.business.entity_type)

    if request.business.gstin:
        validate_gstin(
            request.business.gstin,
            pan=request.business.pan,
            state=request.profile.state if request.profile else None,
        )

    if request.business.cin:
        validate_cin(
            request.business.cin,
            entity_type=request.business.entity_type,
            incorporation_date=request.business.incorporation_date,
        )

    if request.business.udyam_number:
        validate_udyam_number(request.business.udyam_number)

    # 2. Location Validation
    if request.profile and request.profile.pincode:
        validate_pincode(request.profile.pincode)

    # 3. Auto-classify CPCB if missing
    if request.profile and not request.profile.pollution_category:
        classification = classify_industry(
            nic_code=request.profile.nic_code,
            manufacturing_activity=request.profile.manufacturing_activity,
            power_kw=request.profile.power_requirement_kw,
        )
        request.profile.pollution_category = classification.category

    # 4. Execute Onboarding
    business, next_steps = await onboard_business(db, current_user, request)

    return OnboardingResponse(
        business=business,
        message=f"Enterprise '{business.legal_name}' onboarded successfully.",
        next_steps=next_steps,
    )


@router.get("/my-businesses", response_model=List[BusinessResponse])
async def list_my_businesses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[BusinessResponse]:
    """
    Retrieve all industrial enterprises registered by or accessible to current user.
    """
    return await get_user_businesses(db, current_user)


@router.get("/{business_id}", response_model=BusinessResponse)
async def get_business(
    business_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BusinessResponse:
    """
    Retrieve business entity and operational profile by ID.
    """
    return await get_business_by_id(db, business_id, current_user)


@router.put("/{business_id}", response_model=BusinessResponse)
async def update_business_details(
    business_id: str,
    update_data: BusinessUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BusinessResponse:
    """
    Update core enterprise legal structure and statutory numbers.
    """
    if update_data.pan:
        validate_pan(update_data.pan, update_data.entity_type)
    if update_data.gstin:
        validate_gstin(update_data.gstin, pan=update_data.pan)
    if update_data.cin:
        validate_cin(update_data.cin, entity_type=update_data.entity_type)

    return await update_business(db, business_id, update_data, current_user)


@router.put("/{business_id}/profile", response_model=BusinessProfileResponse)
async def update_profile_details(
    business_id: str,
    profile_data: BusinessProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BusinessProfileResponse:
    """
    Update industrial operational profile and recalculate completeness.
    """
    if profile_data.pincode:
        validate_pincode(profile_data.pincode)

    return await update_business_profile(db, business_id, profile_data, current_user)


@router.get("/{business_id}/completeness")
async def get_business_completeness(
    business_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Compute detailed profile completeness report, pillar scores, and approval readiness.
    """
    business = await get_business_by_id(db, business_id, current_user)
    report = evaluate_profile_completeness(business, business.profile)

    return {
        "business_id": business.id,
        "legal_name": business.legal_name,
        "total_score": report.total_score,
        "is_ready_for_approvals": report.is_ready_for_approvals,
        "sections": {
            k: {
                "name": v.name,
                "weight": v.weight,
                "score": v.score,
                "missing_fields": v.missing_fields,
            }
            for k, v in report.sections.items()
        },
        "missing_mandatory_fields": report.missing_mandatory_fields,
        "missing_recommended_fields": report.missing_recommended_fields,
        "actionable_recommendations": report.actionable_recommendations,
    }
