"""
Approval domain model representing statutory clearances, permits, licenses, and NOCs
issued by central/state government departments and regulatory authorities.
"""

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Approval(BaseModel):
    """
    Statutory approval/clearance catalog item (e.g. Consent to Establish, Fire NOC,
    Factory License, Environmental Clearance).
    """
    __tablename__ = "approvals"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Standardized clearance code (e.g. CTE_PCB, FIRE_PROV)",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Full regulatory clearance title",
    )
    department_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Issuing department code (e.g. SPCB, DISH, FIRE, DISCOM)",
    )
    issuing_authority: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Competent authority name (e.g. State Pollution Control Board)",
    )
    statutory_act: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Governing statute or act (e.g. Water Act 1974, Factories Act 1948)",
    )
    validity_period_months: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Statutory validity in months (None if perpetual/one-time)",
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="True if mandatory for applicable units; False if conditional",
    )
    sla_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
        doc="Statutory Public Service Guarantee SLA turnaround days",
    )
    estimated_fee_base: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Base statutory processing fee in INR",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Comprehensive statutory instructions, criteria, and scope",
    )

    def __repr__(self) -> str:
        return f"<Approval code='{self.code}' title='{self.title}'>"
