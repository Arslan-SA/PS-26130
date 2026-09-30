"""
Pydantic schemas for Approval catalog items, requirement discovery, and compliance summaries.
"""

from datetime import datetime
from enum import Enum
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


class ChecklistItemRead(BaseModel):
    """Individual checklist item schema."""
    item_id: str
    title: str
    category: str
    description: str
    is_mandatory: bool
    template_url: Optional[str] = None


class ApprovalChecklistRead(BaseModel):
    """Full statutory checklist schema."""
    approval_code: str
    approval_title: str
    issuing_authority: str
    statutory_act: str
    items: List[ChecklistItemRead]


class GraphNode(BaseModel):
    """DAG node representing an individual clearance requirement."""
    id: str
    requirement_id: str
    title: str
    department_code: str
    issuing_authority: str
    stage: RequirementStage
    status: RequirementStatus
    is_unlocked: bool
    missing_prerequisites: List[str]
    estimated_fee: float
    sla_days: int
    priority: int


class GraphEdge(BaseModel):
    """DAG edge representing a prerequisite dependency."""
    id: str
    source: str
    target: str
    dependency_type: str
    description: Optional[str] = None


class DependencyGraphResponse(BaseModel):
    """Complete statutory clearance DAG response."""
    business_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    topological_order: List[str]
    critical_path: List[str]
    critical_path_days: int


class RoadmapActivityRead(BaseModel):
    """Activity entry along the statutory clearance timeline."""
    approval_code: str
    requirement_id: str
    title: str
    department_code: str
    stage: RequirementStage
    status: RequirementStatus
    sla_days: int
    estimated_fee: float
    start_day_offset: int
    finish_day_offset: int
    scheduled_start: str
    scheduled_finish: str
    is_critical: bool
    prerequisites: List[str]


class RoadmapMilestoneRead(BaseModel):
    """Milestone phase along the roadmap."""
    phase_id: str
    title: str
    description: str
    start_day: int
    finish_day: int
    scheduled_start: str
    scheduled_finish: str
    activity_count: int
    total_estimated_fee: float


class RoadmapPlanResponse(BaseModel):
    """Complete personalized statutory roadmap."""
    business_id: str
    base_start_date: str
    projected_commissioning_date: str
    total_calendar_days: int
    critical_path_days: int
    activities: List[RoadmapActivityRead]
    milestones: List[RoadmapMilestoneRead]


class ActionPriority(str, Enum):
    """Urgency tier for statutory next actions."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionType(str, Enum):
    """Categorical classification of the statutory action required."""
    APPLY_NOW = "APPLY_NOW"
    PREPARE_DOCS = "PREPARE_DOCS"
    PAY_FEES = "PAY_FEES"
    TRACK_SLA = "TRACK_SLA"
    RESOLVE_PREREQUISITES = "RESOLVE_PREREQUISITES"
    DOWNLOAD_CERTIFICATE = "DOWNLOAD_CERTIFICATE"


class NextActionItemRead(BaseModel):
    """Immediate actionable statutory clearance task."""
    approval_code: str
    requirement_id: str
    approval_id: str
    title: str
    department_code: str
    stage: RequirementStage
    current_status: RequirementStatus
    action_type: ActionType
    priority: ActionPriority
    priority_score: int
    headline: str
    rationale: str
    sla_days: int
    estimated_fee: float
    is_critical_path: bool
    is_unlocked: bool
    blocked_by: List[str]
    target_url: str


class NextActionSummaryResponse(BaseModel):
    """Summary of prioritized next statutory actions across enterprise portfolio."""
    business_id: str
    total_clearances: int
    ready_to_act_count: int
    critical_path_actions_count: int
    blocked_count: int
    under_review_count: int
    completed_count: int
    top_immediate_action: Optional[NextActionItemRead] = None
    actions: List[NextActionItemRead]



