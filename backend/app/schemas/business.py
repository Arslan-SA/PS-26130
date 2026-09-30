"""
Pydantic schemas for Business registration, operational profile, and onboarding workflows.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.business import EntityType, MSMECategory
from app.models.business_profile import IndustryScale, PollutionCategory


class BusinessProfileBase(BaseModel):
    """Base schema for industrial operational profile attributes."""
    nic_code: Optional[str] = Field(None, max_length=10, description="National Industrial Classification 5-digit code")
    manufacturing_activity: Optional[str] = Field(None, max_length=500, description="Description of manufacturing/service activity")
    products_services: Optional[str] = Field(None, description="Products manufactured or services rendered")
    industry_scale: IndustryScale = Field(default=IndustryScale.SMALL_SCALE, description="Operational scale")
    pollution_category: Optional[PollutionCategory] = Field(None, description="CPCB Red/Orange/Green/White category")
    state: Optional[str] = Field(None, max_length=100, description="State of operation")
    district: Optional[str] = Field(None, max_length=100, description="District")
    city: Optional[str] = Field(None, max_length=100, description="City / Town")
    pincode: Optional[str] = Field(None, min_length=6, max_length=6, description="6-digit postal code")
    full_address: Optional[str] = Field(None, description="Complete street address")
    plot_number: Optional[str] = Field(None, max_length=50, description="Plot or Survey number")
    industrial_area: Optional[str] = Field(None, max_length=255, description="Name of Industrial Park / MIDC / GIDC zone")
    latitude: Optional[float] = Field(None, description="Geographical latitude")
    longitude: Optional[float] = Field(None, description="Geographical longitude")
    total_employees: Optional[int] = Field(None, ge=0, description="Total workforce count")
    plant_machinery_investment: Optional[float] = Field(None, ge=0.0, description="Investment in plant and machinery in INR")
    land_area_sqm: Optional[float] = Field(None, ge=0.0, description="Total plot/built-up area in square meters")
    annual_turnover: Optional[float] = Field(None, ge=0.0, description="Annual turnover in INR")
    power_requirement_kw: Optional[float] = Field(None, ge=0.0, description="Connected electrical load in kW")
    water_requirement_kld: Optional[float] = Field(None, ge=0.0, description="Daily water demand in KLD")
    contact_person: Optional[str] = Field(None, max_length=255, description="Plant manager or designated representative")
    contact_phone: Optional[str] = Field(None, max_length=20, description="Representative contact phone")
    contact_email: Optional[str] = Field(None, max_length=255, description="Representative contact email")


class BusinessProfileCreate(BusinessProfileBase):
    """Payload to create an operational profile."""
    pass


class BusinessProfileUpdate(BaseModel):
    """Payload to partially update an operational profile."""
    nic_code: Optional[str] = None
    manufacturing_activity: Optional[str] = None
    products_services: Optional[str] = None
    industry_scale: Optional[IndustryScale] = None
    pollution_category: Optional[PollutionCategory] = None
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    full_address: Optional[str] = None
    plot_number: Optional[str] = None
    industrial_area: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_employees: Optional[int] = None
    plant_machinery_investment: Optional[float] = None
    land_area_sqm: Optional[float] = None
    annual_turnover: Optional[float] = None
    power_requirement_kw: Optional[float] = None
    water_requirement_kld: Optional[float] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None


class BusinessProfileResponse(BusinessProfileBase):
    """Public representation of an industrial profile."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    profile_completeness: int
    is_profile_complete: bool
    created_at: datetime
    updated_at: datetime


class BusinessBase(BaseModel):
    """Base legal enterprise attributes."""
    legal_name: str = Field(..., min_length=2, max_length=255, description="Registered legal name of business")
    trade_name: Optional[str] = Field(None, max_length=255, description="Trade or brand name")
    entity_type: EntityType = Field(default=EntityType.PRIVATE_LIMITED, description="Legal structure")
    pan: str = Field(..., min_length=10, max_length=10, description="10-character Permanent Account Number")
    gstin: Optional[str] = Field(None, min_length=15, max_length=15, description="15-character Goods and Services Tax Identification Number")
    udyam_number: Optional[str] = Field(None, max_length=25, description="MSME Udyam Registration Number")
    cin: Optional[str] = Field(None, min_length=21, max_length=21, description="Corporate Identification Number (for LLPs/Companies)")
    msme_category: MSMECategory = Field(default=MSMECategory.MICRO, description="MSME classification")
    incorporation_date: Optional[date] = Field(None, description="Date of legal incorporation")
    website: Optional[str] = Field(None, max_length=255, description="Company website URL")


class BusinessCreate(BusinessBase):
    """Payload to create/register a new business."""
    pass


class BusinessUpdate(BaseModel):
    """Payload to partially update enterprise details."""
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    entity_type: Optional[EntityType] = None
    pan: Optional[str] = None
    gstin: Optional[str] = None
    udyam_number: Optional[str] = None
    cin: Optional[str] = None
    msme_category: Optional[MSMECategory] = None
    incorporation_date: Optional[date] = None
    website: Optional[str] = None


class BusinessResponse(BusinessBase):
    """Public representation of a Business entity with attached profile."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    is_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    profile: Optional[BusinessProfileResponse] = None


class OnboardingRequest(BaseModel):
    """Unified payload for initial business onboarding."""
    business: BusinessCreate
    profile: Optional[BusinessProfileCreate] = None


class OnboardingResponse(BaseModel):
    """Result of business onboarding orchestration."""
    business: BusinessResponse
    message: str
    next_steps: list[str]
