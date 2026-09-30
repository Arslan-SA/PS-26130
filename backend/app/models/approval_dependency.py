"""
Approval dependency domain model representing statutory prerequisite graphs and
regulatory sequencing constraints between clearances.
"""

from enum import Enum
from sqlalchemy import Enum as SQLEnum, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class DependencyType(str, Enum):
    """Nature of statutory constraint connecting two clearances."""
    MANDATORY_PREREQUISITE = "MANDATORY_PREREQUISITE"    # A must be granted before B can be applied/granted
    RECOMMENDED_PARALLEL = "RECOMMENDED_PARALLEL"        # Can be processed simultaneously to compress lead times
    CONDITIONAL = "CONDITIONAL"                          # Dependent on specific operational conditions


class ApprovalDependency(BaseModel):
    """
    Directed dependency edge in the statutory approval DAG.
    Encodes that `from_approval_code` is a prerequisite for `to_approval_code`.
    """
    __tablename__ = "approval_dependencies"
    __table_args__ = (
        UniqueConstraint("from_approval_code", "to_approval_code", name="uq_approval_dependency"),
    )

    from_approval_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Precedent / Prerequisite approval code (e.g. CTE_PCB, FIRE_NOC)",
    )
    to_approval_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Dependent approval code (e.g. CTO_PCB, FACTORY_LIC)",
    )
    dependency_type: Mapped[DependencyType] = mapped_column(
        SQLEnum(DependencyType, name="dependency_type_enum"),
        default=DependencyType.MANDATORY_PREREQUISITE,
        nullable=False,
        index=True,
        doc="Type of dependency constraint",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Statutory explanation of why this precedence constraint exists",
    )
    enacted_statute: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Governing statute mandating precedence (e.g. Factories Act 1948 Sec 6)",
    )

    def __repr__(self) -> str:
        return f"<ApprovalDependency {self.from_approval_code} -> {self.to_approval_code} ({self.dependency_type.value})>"
