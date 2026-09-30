"""
Pydantic schemas for Approval catalog items, requirement discovery, and compliance summaries.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.approval_requirement import RequirementStage, RequirementStatus


class ApprovalRead(BaseModel):
    """Catalog clearance entity."""
    id: str
    code: str
    title: str
    department_code: str
    issuing_authority: str
    statutory_act: Optional[str] = None
    validity_period_months: Optional[int] = None
    is_mandatory: bool
    sla_days: int
    estimated_fee_base: float
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalRequirementRead(BaseModel):
    """Requirement mapped to a specific business unit."""
    id: str
    business_id: str
    approval_id: str
    status: RequirementStatus
    stage: RequirementStage
    priority: int
    is_mandatory: bool
    trigger_reason: str
    estimated_fee: float
    sla_deadline_days: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    approval: Optional[ApprovalRead] = None

    model_config = ConfigDict(from_attributes=True)


class ClearanceSummaryRead(BaseModel):
    """Consolidated compliance and fee summary metrics."""
    business_id: str
    total_requirements: int
    mandatory_requirements: int
    total_estimated_fee: float
    pre_establishment_critical_days: int
    by_stage: Dict[str, int]
    by_department: Dict[str, int]
    status_breakdown: Dict[str, int]


class DiscoveryResponse(BaseModel):
    """Response returned when clearance discovery is executed."""
    business_id: str
    count: int
    requirements: List[ApprovalRequirementRead]
    summary: ClearanceSummaryRead
