"""
Approval requirement domain model linking an enterprise business unit to statutory
clearances identified by the regulatory evaluation engine.
"""

from enum import Enum
import uuid
from sqlalchemy import Boolean, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class RequirementStatus(str, Enum):
    """Lifecycle status of a mandatory/conditional clearance requirement."""
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXEMPTED = "EXEMPTED"


class RequirementStage(str, Enum):
    """Statutory commissioning stage when this clearance must be obtained."""
    PRE_ESTABLISHMENT = "PRE_ESTABLISHMENT"      # Prior to construction (e.g. CTE, Land Conversion)
    PRE_COMMISSIONING = "PRE_COMMISSIONING"      # Prior to trial runs (e.g. CTO, Fire Safety NOC)
    POST_COMMISSIONING = "POST_COMMISSIONING"    # Prior to commercial ops (e.g. Factory License, Boiler Registration)
    REGULAR_OPERATIONS = "REGULAR_OPERATIONS"    # Recurring/operational compliance


class ApprovalRequirement(BaseModel):
    """
    Instance of an approval requirement mapped to a specific enterprise business,
    including trigger rationale, commissioning stage, estimated fees, and current progress.
    """
    __tablename__ = "approval_requirements"
    __table_args__ = (
        UniqueConstraint("business_id", "approval_id", name="uq_business_approval_requirement"),
    )

    business_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target enterprise business requiring this clearance",
    )
    approval_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("approvals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Statutory clearance catalog entry",
    )
    status: Mapped[RequirementStatus] = mapped_column(
        SQLEnum(RequirementStatus, name="requirement_status_enum"),
        default=RequirementStatus.NOT_STARTED,
        nullable=False,
        index=True,
        doc="Current clearance fulfillment state",
    )
    stage: Mapped[RequirementStage] = mapped_column(
        SQLEnum(RequirementStage, name="requirement_stage_enum"),
        default=RequirementStage.PRE_ESTABLISHMENT,
        nullable=False,
        index=True,
        doc="Industrial stage when clearance must be in hand",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Priority level: 1 (Urgent / Blocker) to 5 (Informational)",
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Indicates statutory compulsion (True) vs conditional optionality (False)",
    )
    trigger_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Statutory justification explaining why this clearance is required for this enterprise",
    )
    estimated_fee: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Calculated government processing fee based on capital investment and scale",
    )
    sla_deadline_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
        doc="Service Guarantee Act statutory maximum SLA in days",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Custom officer remarks or enterprise compliance notes",
    )

    # Relationships
    business = relationship("Business", backref="approval_requirements", lazy="selectin")
    approval = relationship("Approval", lazy="selectin")
    status_history = relationship(
        "ApprovalStatusHistory",
        back_populates="requirement",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(ApprovalStatusHistory.created_at)",
    )

    def __repr__(self) -> str:
        return (
            f"<ApprovalRequirement business_id='{self.business_id}' "
            f"approval_id='{self.approval_id}' status='{self.status.value}'>"
        )
