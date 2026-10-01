"""
Application domain model representing statutory single-window filings (Fragment 76).
Tracks end-to-end multi-department approvals lifecycle, statutory scrutiny,
deficiencies, inspections, and formal clearance grants.
"""

from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.approval import Approval
    from app.models.approval_requirement import ApprovalRequirement
    from app.models.application_query import ApplicationQuery
    from app.models.application_status_history import ApplicationStatusHistory
    from app.models.business import Business
    from app.models.department import Department
    from app.models.inspection import Inspection
    from app.models.user import User


class ApplicationStatus(str, Enum):
    """Statutory clearance application lifecycle statuses."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    QUERY_RAISED = "QUERY_RAISED"
    RESUBMITTED = "RESUBMITTED"
    INSPECTION_SCHEDULED = "INSPECTION_SCHEDULED"
    INSPECTION_COMPLETED = "INSPECTION_COMPLETED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class Application(BaseModel):
    """
    Statutory clearance application submitted by an industrial enterprise
    to a designated government regulatory department.
    """
    __tablename__ = "applications"

    application_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Canonical tracking number, e.g. APP-20261001-A1B2",
    )
    business_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target enterprise business unit filing the application",
    )
    approval_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("approvals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Statutory clearance catalog item applied for",
    )
    requirement_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("approval_requirements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional link to business approval requirement",
    )
    department_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Target regulatory department handling the scrutiny",
    )
    department_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Department code for fast partitioning (e.g. SPCB, DISH, FIRE)",
    )
    applied_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User ID of industrial promoter or consultant filing application",
    )
    assigned_officer_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User ID of designated department scrutiny officer",
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, name="application_status_enum", native_enum=False),
        default=ApplicationStatus.DRAFT,
        nullable=False,
        index=True,
        doc="Current lifecycle state in multi-department workflow",
    )
    application_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Statutory form payload (unit details, emissions, power demand, site specs)",
    )
    attached_document_ids: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        doc="List of document UUIDs attached as statutory verification evidence",
    )
    fee_amount: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Calculated statutory processing fee in INR",
    )
    fee_paid: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="True once statutory treasury challan/payment is confirmed",
    )
    fee_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="e-Challan transaction or Bharatkosh receipt reference",
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when formally submitted by applicant",
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when scrutiny commenced by officer",
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of final approval or rejection decision",
    )
    sla_due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="Public Service Guarantee Act statutory SLA deadline",
    )
    approval_certificate_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Official certificate/license number generated upon grant",
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Statutory legal grounds in case of clearance refusal",
    )
    validity_years: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Permit validity duration in years",
    )
    certificate_valid_until: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Clearance expiration date",
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        lazy="selectin",
    )
    approval: Mapped["Approval"] = relationship(
        "Approval",
        lazy="selectin",
    )
    requirement: Mapped[Optional["ApprovalRequirement"]] = relationship(
        "ApprovalRequirement",
        lazy="selectin",
    )
    department: Mapped[Optional["Department"]] = relationship(
        "Department",
        lazy="selectin",
    )
    applicant: Mapped["User"] = relationship(
        "User",
        foreign_keys=[applied_by_user_id],
        lazy="selectin",
    )
    assigned_officer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_officer_id],
        lazy="selectin",
    )
    status_history: Mapped[List["ApplicationStatusHistory"]] = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(ApplicationStatusHistory.created_at)",
    )
    queries: Mapped[List["ApplicationQuery"]] = relationship(
        "ApplicationQuery",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(ApplicationQuery.created_at)",
    )
    inspections: Mapped[List["Inspection"]] = relationship(
        "Inspection",
        back_populates="application",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(Inspection.scheduled_date)",
    )

    def __repr__(self) -> str:
        return f"<Application {self.application_number} status={self.status.value} dept={self.department_code}>"
