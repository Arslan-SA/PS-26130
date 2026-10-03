"""
Pydantic schemas for Compliance & Monitoring (Phase 7, Fragments 91–102).
Defines request/response payloads for compliance requirements, compliance records,
dashboard metrics, alerts, and prioritized compliance views.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.compliance import (
    ComplianceCategory,
    ComplianceFrequency,
    CompliancePriority,
    ComplianceRecordStatus,
)


# ---------------------------------------------------------------------------
# Compliance Requirement Schemas
# ---------------------------------------------------------------------------

class ComplianceRequirementRead(BaseModel):
    """Serialized compliance requirement definition."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    approval_id: str
    code: str
    title: str
    description: Optional[str] = None
    category: ComplianceCategory
    frequency: ComplianceFrequency
    frequency_months: int
    priority: CompliancePriority
    warning_days: int
    statutory_act: Optional[str] = None
    penalty_description: Optional[str] = None
    penalty_amount_max: float
    required_documents: List[str] = []
    applicable_pollution_categories: List[str] = []
    applicable_industry_scales: List[str] = []
    is_mandatory: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ComplianceRequirementListResponse(BaseModel):
    """Paginated list of compliance requirements."""
    total: int
    items: List[ComplianceRequirementRead]


# ---------------------------------------------------------------------------
# Compliance Record Schemas
# ---------------------------------------------------------------------------

class ComplianceRecordCreate(BaseModel):
    """Payload for manually initiating a compliance filing."""
    requirement_id: str = Field(..., description="ID of the compliance requirement")
    business_id: str = Field(..., description="ID of the business entity")
    cycle_label: str = Field(..., min_length=1, max_length=50, description="Cycle identifier (e.g., 'FY2026-27')")
    due_date: date = Field(..., description="Statutory deadline for this cycle")
    filing_data: Dict[str, Any] = Field(default_factory=dict, description="Structured filing form data")
    evidence_document_ids: List[str] = Field(default_factory=list, description="Uploaded evidence document IDs")
    remarks: Optional[str] = Field(None, description="Applicant notes")


class ComplianceRecordUpdate(BaseModel):
    """Payload to update a compliance record (submit filing, add evidence)."""
    filing_data: Optional[Dict[str, Any]] = None
    evidence_document_ids: Optional[List[str]] = None
    remarks: Optional[str] = None


class ComplianceRecordSubmitPayload(BaseModel):
    """Payload when industry user submits a compliance filing."""
    filing_data: Dict[str, Any] = Field(default_factory=dict, description="Completed filing responses")
    evidence_document_ids: List[str] = Field(default_factory=list, description="Evidence documents")
    remarks: Optional[str] = Field(None, description="Submission notes")


class ComplianceRecordReviewPayload(BaseModel):
    """Officer payload for reviewing a compliance filing."""
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$", description="Review outcome")
    officer_remarks: Optional[str] = Field(None, description="Officer notes")
    new_valid_until: Optional[date] = Field(None, description="New validity if approved (renewal)")
    penalty_imposed: float = Field(0.0, ge=0.0, description="Penalty for late/non-compliance")


class ComplianceRecordRead(BaseModel):
    """Full serialized compliance record."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    requirement_id: str
    application_id: Optional[str] = None
    status: ComplianceRecordStatus
    cycle_label: str
    due_date: date
    warning_date: Optional[date] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    new_valid_until: Optional[date] = None
    evidence_document_ids: List[str] = []
    filing_data: Dict[str, Any] = {}
    remarks: Optional[str] = None
    officer_remarks: Optional[str] = None
    penalty_imposed: float = 0.0
    days_overdue: int = 0
    responsible_user_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Enriched fields (from joins)
    requirement_code: Optional[str] = None
    requirement_title: Optional[str] = None
    requirement_category: Optional[ComplianceCategory] = None
    requirement_priority: Optional[CompliancePriority] = None
    requirement_frequency: Optional[ComplianceFrequency] = None
    business_name: Optional[str] = None


class ComplianceRecordSummary(BaseModel):
    """Lightweight summary for dashboard cards."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    requirement_id: str
    status: ComplianceRecordStatus
    cycle_label: str
    due_date: date
    days_overdue: int = 0
    requirement_code: Optional[str] = None
    requirement_title: Optional[str] = None
    requirement_category: Optional[ComplianceCategory] = None
    requirement_priority: Optional[CompliancePriority] = None
    penalty_imposed: float = 0.0
    created_at: datetime


class ComplianceRecordListResponse(BaseModel):
    """Paginated list of compliance records."""
    total: int
    items: List[ComplianceRecordSummary]


# ---------------------------------------------------------------------------
# Compliance Dashboard & Alerts Schemas (Fragments 94, 97, 98, 99)
# ---------------------------------------------------------------------------

class ComplianceDashboardMetrics(BaseModel):
    """Aggregate compliance health metrics for a business entity."""
    business_id: str
    total_obligations: int
    compliant_count: int
    due_soon_count: int
    overdue_count: int
    in_progress_count: int
    submitted_count: int
    exempted_count: int
    expired_count: int
    compliance_rate_percent: float
    total_penalty_exposure: float
    total_penalties_imposed: float
    next_deadline: Optional[date] = None
    most_critical_item: Optional[str] = None


class ComplianceAlert(BaseModel):
    """Individual compliance alert notification."""
    id: str
    record_id: str
    requirement_code: str
    requirement_title: str
    category: ComplianceCategory
    priority: CompliancePriority
    alert_type: str  # "DUE_SOON", "OVERDUE", "EXPIRING", "PENALTY_RISK"
    message: str
    due_date: date
    days_remaining: int  # Negative means overdue
    penalty_exposure: float
    business_id: str
    business_name: Optional[str] = None


class ComplianceAlertListResponse(BaseModel):
    """List of active compliance alerts."""
    total: int
    critical_count: int
    high_count: int
    items: List[ComplianceAlert]


class CompliancePrioritizedItem(BaseModel):
    """Compliance item ranked by urgency/severity for action queue."""
    rank: int
    record_id: str
    requirement_code: str
    requirement_title: str
    category: ComplianceCategory
    priority: CompliancePriority
    status: ComplianceRecordStatus
    due_date: date
    days_remaining: int
    penalty_exposure: float
    urgency_score: float  # Computed composite score
    recommended_action: str
    business_id: str


class CompliancePrioritizedListResponse(BaseModel):
    """Prioritized compliance action queue."""
    total: int
    items: List[CompliancePrioritizedItem]


class ComplianceStatusSummary(BaseModel):
    """Business-level compliance status breakdown per category."""
    category: ComplianceCategory
    total: int
    compliant: int
    due_soon: int
    overdue: int
    expired: int
    compliance_rate_percent: float


class ComplianceStatusResponse(BaseModel):
    """Full compliance status report for a business."""
    business_id: str
    overall_compliance_rate: float
    overall_health: str  # "HEALTHY", "AT_RISK", "NON_COMPLIANT"
    category_breakdown: List[ComplianceStatusSummary]
    recent_deadlines: List[ComplianceRecordSummary]
    upcoming_deadlines: List[ComplianceRecordSummary]
