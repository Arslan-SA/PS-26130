"""
Department domain model representing regulatory authorities, statutory directorates,
and competent licensing boards across Central, State, and Municipal jurisdictions.
"""

from enum import Enum
from sqlalchemy import Enum as SQLEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class JurisdictionLevel(str, Enum):
    """Statutory tier of administrative authority."""
    CENTRAL = "CENTRAL"          # e.g., CPCB, MoEFCC, PESO, CGWA
    STATE = "STATE"              # e.g., MPCB, DISH Maharashtra, Fire Services
    MUNICIPAL = "MUNICIPAL"      # e.g., Municipal Corporation, Urban Local Body


class Department(BaseModel):
    """
    Government department or statutory board responsible for granting industrial
    approvals, inspections, and enforcement.
    """
    __tablename__ = "departments"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Standard department identifier code (e.g. SPCB, DISH, FIRE, DISCOM, CGWA, PESO)",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Full formal department title",
    )
    jurisdiction_level: Mapped[JurisdictionLevel] = mapped_column(
        SQLEnum(JurisdictionLevel, name="jurisdiction_level_enum"),
        default=JurisdictionLevel.STATE,
        nullable=False,
        index=True,
        doc="Level of governance (CENTRAL, STATE, MUNICIPAL)",
    )
    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="State of jurisdiction (None if CENTRAL)",
    )
    nodal_officer_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Designated single-window nodal officer",
    )
    nodal_officer_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Contact email for clearance queries and escalations",
    )
    nodal_officer_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        doc="Official telephone/helpline number",
    )
    website_portal: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Official departmental Single Window System (SWS) integration URL",
    )
    grievance_portal: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Statutory grievance / appeal portal link",
    )
    standard_sla_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
        doc="Department-wide baseline Public Service Guarantee SLA turnaround days",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Scope of departmental authority and regulatory mandate",
    )

    def __repr__(self) -> str:
        return f"<Department code='{self.code}' name='{self.name}'>"
