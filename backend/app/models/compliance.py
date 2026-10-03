"""
Compliance domain models for post-approval statutory obligations (Fragments 91–92).

ComplianceRequirement: Defines a recurring statutory compliance obligation
    (e.g., "Annual CTO Renewal", "Quarterly Hazardous Waste Returns").
ComplianceRecord: Tracks each individual compliance filing/renewal instance
    with deadlines, status, evidence, and penalty exposure.
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
    from app.models.application import Application
    from app.models.business import Business
    from app.models.user import User


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ComplianceFrequency(str, Enum):
    """How often a statutory compliance obligation recurs."""
    ONE_TIME = "ONE_TIME"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    HALF_YEARLY = "HALF_YEARLY"
    ANNUAL = "ANNUAL"
    BIENNIAL = "BIENNIAL"           # Every 2 years
    QUINQUENNIAL = "QUINQUENNIAL"   # Every 5 years
    EVENT_DRIVEN = "EVENT_DRIVEN"   # Triggered by specific events


class CompliancePriority(str, Enum):
    """Business priority classification for compliance obligations."""
    CRITICAL = "CRITICAL"     # Failure = shutdown / criminal prosecution
    HIGH = "HIGH"             # Failure = significant penalty / show-cause
    MEDIUM = "MEDIUM"         # Failure = moderate penalty / warning
    LOW = "LOW"               # Advisory / best-practice


class ComplianceRecordStatus(str, Enum):
    """Status of an individual compliance filing/renewal cycle."""
    UPCOMING = "UPCOMING"             # Not yet due
    DUE_SOON = "DUE_SOON"            # Within warning window
    OVERDUE = "OVERDUE"               # Past deadline
    IN_PROGRESS = "IN_PROGRESS"       # Filing initiated
    SUBMITTED = "SUBMITTED"           # Filing submitted to authority
    UNDER_REVIEW = "UNDER_REVIEW"     # Under departmental review
    APPROVED = "APPROVED"             # Compliance confirmed/renewed
    REJECTED = "REJECTED"             # Filing rejected, remediation needed
    EXEMPTED = "EXEMPTED"             # Exempted by regulatory authority
    EXPIRED = "EXPIRED"               # Permit/license has expired without renewal


class ComplianceCategory(str, Enum):
    """Regulatory domain category for compliance obligations."""
    ENVIRONMENTAL = "ENVIRONMENTAL"
    LABOR = "LABOR"
    FIRE_SAFETY = "FIRE_SAFETY"
    FACTORY_OPERATIONS = "FACTORY_OPERATIONS"
    BOILER_PRESSURE = "BOILER_PRESSURE"
    ELECTRICAL = "ELECTRICAL"
    TAX_STATUTORY = "TAX_STATUTORY"
    LAND_ZONING = "LAND_ZONING"
    OTHER = "OTHER"


# ---------------------------------------------------------------------------
# Fragment 91: ComplianceRequirement
# ---------------------------------------------------------------------------

class ComplianceRequirement(BaseModel):
    """
    Defines a statutory recurring compliance obligation tied to an approval
    catalog item. Examples: "CTO Renewal every 5 years", "Annual Hazardous
    Waste Returns to SPCB", "Quarterly Factory Safety Audit".
    """
    __tablename__ = "compliance_requirements"

    approval_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("approvals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Statutory clearance catalog item this obligation stems from",
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Machine-readable compliance code (e.g. CTO_RENEWAL, HW_RETURNS_Q)",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Human-readable obligation title",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed regulatory description and instructions",
    )
    category: Mapped[ComplianceCategory] = mapped_column(
        SQLEnum(ComplianceCategory, name="compliance_category_enum", native_enum=False),
        default=ComplianceCategory.OTHER,
        nullable=False,
        index=True,
        doc="Regulatory domain grouping",
    )
    frequency: Mapped[ComplianceFrequency] = mapped_column(
        SQLEnum(ComplianceFrequency, name="compliance_frequency_enum", native_enum=False),
        default=ComplianceFrequency.ANNUAL,
        nullable=False,
        index=True,
        doc="Recurrence interval for the obligation",
    )
    frequency_months: Mapped[int] = mapped_column(
        Integer,
        default=12,
        nullable=False,
        doc="Numeric recurrence interval in months (12=annual, 3=quarterly)",
    )
    priority: Mapped[CompliancePriority] = mapped_column(
        SQLEnum(CompliancePriority, name="compliance_priority_enum", native_enum=False),
        default=CompliancePriority.HIGH,
        nullable=False,
        index=True,
        doc="Severity classification if obligation is not met",
    )
    warning_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
        doc="Days before deadline to trigger DUE_SOON alert",
    )
    statutory_act: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Governing statute (e.g., Water Act 1974, Factories Act 1948)",
    )
    penalty_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Regulatory consequences for non-compliance",
    )
    penalty_amount_max: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Maximum statutory penalty exposure in INR",
    )
    required_documents: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        doc="Document types required for this compliance filing",
    )
    applicable_pollution_categories: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        doc="Applicable CPCB pollution categories (RED, ORANGE, GREEN, WHITE)",
    )
    applicable_industry_scales: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        doc="Applicable industry scale tiers (SMALL_SCALE, MEDIUM_SCALE, etc.)",
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether compliance is mandatory for all applicable businesses",
    )

    # Relationships
    approval: Mapped["Approval"] = relationship("Approval", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ComplianceRequirement code='{self.code}' freq={self.frequency.value}>"


# ---------------------------------------------------------------------------
# Fragment 92: ComplianceRecord
# ---------------------------------------------------------------------------

class ComplianceRecord(BaseModel):
    """
    Individual compliance filing/renewal record for a specific business entity.
    Tracks each obligation cycle from upcoming → due → submitted → approved/rejected.
    """
    __tablename__ = "compliance_records"

    business_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Enterprise business unit responsible for this compliance",
    )
    requirement_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("compliance_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Parent compliance requirement definition",
    )
    application_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional linked application if compliance requires formal filing",
    )
    status: Mapped[ComplianceRecordStatus] = mapped_column(
        SQLEnum(ComplianceRecordStatus, name="compliance_record_status_enum", native_enum=False),
        default=ComplianceRecordStatus.UPCOMING,
        nullable=False,
        index=True,
        doc="Current compliance lifecycle status",
    )
    cycle_label: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Human-readable cycle identifier (e.g., '2026-Q3', 'FY2026-27')",
    )
    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        doc="Statutory deadline for this filing/renewal cycle",
    )
    warning_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Date when DUE_SOON alert should activate",
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when filing was submitted",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when compliance was confirmed/approved",
    )
    new_valid_until: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="New validity end date after successful renewal",
    )
    evidence_document_ids: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        doc="Uploaded evidence/filing document UUIDs",
    )
    filing_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Structured filing data (form responses, measurements, etc.)",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Notes from applicant or reviewing officer",
    )
    officer_remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Department officer review notes",
    )
    penalty_imposed: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Actual penalty amount imposed for late/non-compliance (INR)",
    )
    days_overdue: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of days past the deadline (0 if on time)",
    )
    responsible_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User responsible for completing this compliance cycle",
    )

    # Relationships
    business: Mapped["Business"] = relationship("Business", lazy="selectin")
    requirement: Mapped["ComplianceRequirement"] = relationship(
        "ComplianceRequirement",
        lazy="selectin",
    )
    application: Mapped[Optional["Application"]] = relationship(
        "Application",
        lazy="selectin",
    )
    responsible_user: Mapped[Optional["User"]] = relationship(
        "User",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<ComplianceRecord business_id='{self.business_id}' "
            f"req='{self.requirement_id}' cycle='{self.cycle_label}' "
            f"status='{self.status.value}'>"
        )
