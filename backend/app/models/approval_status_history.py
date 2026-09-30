"""
Approval Status History domain model (Fragment 56).
Tracks lifecycle transitions, timestamps, officer remarks, reference numbers,
and audit accountability for statutory approval requirements.
"""

from typing import TYPE_CHECKING, Optional
from sqlalchemy import Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.approval_requirement import RequirementStatus
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.approval_requirement import ApprovalRequirement
    from app.models.user import User


class ApprovalStatusHistory(BaseModel):
    """
    Audit log entry recording an immutable status transition for a statutory approval requirement.
    """
    __tablename__ = "approval_status_histories"

    requirement_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("approval_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target approval requirement instance",
    )
    business_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target enterprise business unit",
    )
    from_status: Mapped[Optional[RequirementStatus]] = mapped_column(
        SQLEnum(RequirementStatus, name="requirement_status_enum", create_constraint=False),
        nullable=True,
        doc="Previous lifecycle status",
    )
    to_status: Mapped[RequirementStatus] = mapped_column(
        SQLEnum(RequirementStatus, name="requirement_status_enum", create_constraint=False),
        nullable=False,
        doc="Target lifecycle status transitioned into",
    )
    changed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User ID of the industrial promoter or government officer who triggered transition",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Notes, regulatory reasons, or officer remarks accompanying transition",
    )
    reference_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Statutory filing receipt, challan ID, or clearance certificate number",
    )

    # Relationships
    requirement: Mapped["ApprovalRequirement"] = relationship(
        "ApprovalRequirement",
        back_populates="status_history",
        lazy="selectin",
    )
    changed_by: Mapped[Optional["User"]] = relationship(
        "User",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<ApprovalStatusHistory req='{self.requirement_id}' "
            f"from='{self.from_status}' to='{self.to_status}' at='{self.created_at}'>"
        )
