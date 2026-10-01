"""
Pydantic schemas for the statutory application workflow engine (Fragments 76–89).
Defines request payloads and serialized responses for application creation, submission,
scrutiny review, deficiency queries, inspections, and final approvals.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.application import ApplicationStatus
from app.models.application_query import QueryStatus
from app.models.inspection import InspectionRecommendation, InspectionStatus


class ApplicationCreate(BaseModel):
    """Payload to create a new draft application."""
    business_id: str = Field(..., description="ID of the business entity applying")
    approval_id: str = Field(..., description="ID of the statutory clearance catalog item")
    requirement_id: Optional[str] = Field(None, description="Optional link to ApprovalRequirement")
    application_data: Dict[str, Any] = Field(default_factory=dict, description="Custom form fields for clearance")
    attached_document_ids: List[str] = Field(default_factory=list, description="List of document IDs attached")
    fee_amount: float = Field(0.0, ge=0.0, description="Statutory fee")
    fee_paid: bool = Field(False, description="Whether fee has already been paid")
    fee_reference: Optional[str] = Field(None, description="e-Challan / Bharatkosh transaction reference")


class ApplicationUpdate(BaseModel):
    """Payload to update an editable draft or query-raised application."""
    application_data: Optional[Dict[str, Any]] = None
    attached_document_ids: Optional[List[str]] = None
    fee_paid: Optional[bool] = None
    fee_reference: Optional[str] = None


class ApplicationSubmitPayload(BaseModel):
    """Payload to formally submit an application for statutory scrutiny."""
    fee_paid: bool = Field(True, description="Statutory fees must be confirmed for submission")
    fee_reference: Optional[str] = Field(None, description="Statutory e-challan or receipt reference number")
    additional_remarks: Optional[str] = Field(None, description="Optional applicant notes for scrutiny officer")


class ApplicationStatusHistoryRead(BaseModel):
    """Serialized audit log entry of application state transition."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    from_status: Optional[ApplicationStatus] = None
    to_status: ApplicationStatus
    changed_by_user_id: Optional[str] = None
    changed_by_name: Optional[str] = None
    action: str
    remarks: Optional[str] = None
    created_at: datetime


class ApplicationQueryCreate(BaseModel):
    """Officer payload to raise a formal deficiency query."""
    document_id: Optional[str] = Field(None, description="Specific document ID with deficiency, if applicable")
    query_title: str = Field(..., min_length=3, max_length=255, description="Brief summary of query")
    query_text: str = Field(..., min_length=10, description="Statutory deficiency description & required action")
    due_date: Optional[date] = Field(None, description="Resolution due date")


class ApplicationQueryRespondPayload(BaseModel):
    """Applicant payload responding to a raised deficiency."""
    response_text: str = Field(..., min_length=5, description="Corrective clarification or compliance explanation")
    response_document_id: Optional[str] = Field(None, description="ID of replacement/clarifying document")


class ApplicationQueryRead(BaseModel):
    """Serialized deficiency query model."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    raised_by_user_id: Optional[str] = None
    raised_by_name: Optional[str] = None
    document_id: Optional[str] = None
    query_title: str
    query_text: str
    status: QueryStatus
    due_date: Optional[date] = None
    response_text: Optional[str] = None
    response_document_id: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class InspectionSchedulePayload(BaseModel):
    """Officer payload to schedule a physical plant site inspection."""
    inspector_id: str = Field(..., description="User ID of appointed field inspector")
    scheduled_date: datetime = Field(..., description="Scheduled inspection timestamp")
    instructions: Optional[str] = Field(None, description="Specific compliance verification checklist/instructions")


class InspectionReportPayload(BaseModel):
    """Inspector payload submitting physical site findings."""
    findings: str = Field(..., min_length=10, description="Site observation findings")
    checklist_results: Dict[str, Any] = Field(default_factory=dict, description="Structured checklist entries")
    recommendation: InspectionRecommendation = Field(..., description="Inspector statutory recommendation")
    geo_latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="GPS Latitude")
    geo_longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="GPS Longitude")
    report_document_id: Optional[str] = Field(None, description="Uploaded signed report/photograph ID")


class InspectionRead(BaseModel):
    """Serialized field inspection record."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    inspector_id: Optional[str] = None
    inspector_name: Optional[str] = None
    department_id: Optional[str] = None
    scheduled_date: datetime
    status: InspectionStatus
    instructions: Optional[str] = None
    findings: Optional[str] = None
    checklist_results: Dict[str, Any]
    recommendation: Optional[InspectionRecommendation] = None
    geo_latitude: Optional[float] = None
    geo_longitude: Optional[float] = None
    report_document_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class StatutoryDeterminationPayload(BaseModel):
    """Officer statutory decision payload (Approval or Rejection)."""
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$", description="Final determination")
    remarks: Optional[str] = Field(None, description="Officer determination notes")
    rejection_reason: Optional[str] = Field(None, description="Legal grounds in case of rejection")
    validity_years: Optional[int] = Field(None, ge=1, le=25, description="Validity period in years if approved")


class ApplicationSummaryRead(BaseModel):
    """Lightweight application summary for queues and dashboards."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_number: str
    business_id: str
    business_name: Optional[str] = None
    approval_id: str
    approval_code: Optional[str] = None
    approval_title: Optional[str] = None
    department_code: str
    department_name: Optional[str] = None
    status: ApplicationStatus
    fee_amount: float
    fee_paid: bool
    submitted_at: Optional[datetime] = None
    sla_due_date: Optional[datetime] = None
    sla_days_remaining: Optional[int] = None
    approval_certificate_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ApplicationDetailRead(ApplicationSummaryRead):
    """Comprehensive application response with nested queries, history, and inspections."""
    model_config = ConfigDict(from_attributes=True)

    requirement_id: Optional[str] = None
    department_id: Optional[str] = None
    applied_by_user_id: str
    applied_by_name: Optional[str] = None
    assigned_officer_id: Optional[str] = None
    assigned_officer_name: Optional[str] = None
    application_data: Dict[str, Any]
    attached_document_ids: List[str]
    fee_reference: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    validity_years: Optional[int] = None
    certificate_valid_until: Optional[date] = None
    status_history: List[ApplicationStatusHistoryRead] = []
    queries: List[ApplicationQueryRead] = []
    inspections: List[InspectionRead] = []


class ApplicationListResponse(BaseModel):
    """Paginated or filtered list of applications."""
    total: int
    items: List[ApplicationSummaryRead]


class OfficerInboxMetrics(BaseModel):
    """Live queue statistics for department officer review portal."""
    pending_scrutiny: int
    under_review: int
    queries_pending_applicant_response: int
    inspections_scheduled: int
    approved_count: int
    rejected_count: int
    sla_critical_count: int
    sla_compliance_rate_percent: float


class OfficerInboxSummaryResponse(BaseModel):
    """Full officer dashboard response."""
    officer_id: str
    full_name: str
    department_id: Optional[str] = None
    department_code: str
    designation: Optional[str] = None
    role: str
    queue_metrics: OfficerInboxMetrics
    next_action: str
