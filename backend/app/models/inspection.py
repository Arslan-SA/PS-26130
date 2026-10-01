"""
Field Inspection domain model (Fragment 86).
Manages statutory on-site plant verification, scheduling, inspector assignment,
geolocated verification, checklist reporting, and compliance recommendations.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.department import Department
    from app.models.document import Document
    from app.models.user import User


class InspectionStatus(str, Enum):
    """Field inspection lifecycle status."""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class InspectionRecommendation(str, Enum):
    """Inspector's statutory recommendation following physical site visit."""
    SATISFACTORY = "SATISFACTORY"
    NON_COMPLIANT = "NON_COMPLIANT"
    REMEDIATION_REQUIRED = "REMEDIATION_REQUIRED"


class Inspection(BaseModel):
    """
    Physical on-site plant inspection record for statutory verification
    (Pollution Control, Fire Safety, Factory Inspectorate, Boiler Inspection).
    """
    __tablename__ = "inspections"

    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target clearance application requiring verification",
    )
    inspector_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Assigned field officer / inspector user ID",
    )
    department_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Department conducting the site visit",
    )
    scheduled_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Scheduled date and time of physical site inspection",
    )
    status: Mapped[InspectionStatus] = mapped_column(
        SQLEnum(InspectionStatus, name="inspection_status_enum", native_enum=False),
        default=InspectionStatus.SCHEDULED,
        nullable=False,
        index=True,
        doc="Inspection execution state",
    )
    instructions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Special instructions, safety equipment notes, or focus areas from scrutiny officer",
    )
    findings: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed narrative of site observations, effluent samples, safety measures",
    )
    checklist_results: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Standardized checklist item responses (e.g. fire_alarms: true, etp_functional: true)",
    )
    recommendation: Mapped[Optional[InspectionRecommendation]] = mapped_column(
        SQLEnum(InspectionRecommendation, name="inspection_recommendation_enum", native_enum=False),
        nullable=True,
        index=True,
        doc="Formal inspector determination",
    )
    geo_latitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="GPS latitude captured at the plant site to verify physical presence",
    )
    geo_longitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="GPS longitude captured at the plant site to verify physical presence",
    )
    report_document_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        doc="Uploaded signed inspection report or photographic evidence",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when inspection report was formally submitted",
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="inspections",
        lazy="selectin",
    )
    inspector: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[inspector_id],
        lazy="selectin",
    )
    department: Mapped[Optional["Department"]] = relationship(
        "Department",
        lazy="selectin",
    )
    report_document: Mapped[Optional["Document"]] = relationship(
        "Document",
        foreign_keys=[report_document_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Inspection id='{self.id}' app='{self.application_id}' status='{self.status.value}'>"
