"""
Application Status History domain model (Fragment 79).
Provides immutable audit trail for all statutory clearance application transitions,
officer actions, timestamps, and regulatory remarks.
"""

from typing import TYPE_CHECKING, Optional
from sqlalchemy import Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.application import ApplicationStatus
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class ApplicationStatusHistory(BaseModel):
    """
    Audit log entry recording an immutable status transition for a statutory clearance application.
    """
    __tablename__ = "application_status_histories"

    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target statutory application instance",
    )
    from_status: Mapped[Optional[ApplicationStatus]] = mapped_column(
        SQLEnum(ApplicationStatus, name="application_status_enum", native_enum=False),
        nullable=True,
        doc="Previous lifecycle status (None if initial draft creation)",
    )
    to_status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, name="application_status_enum", native_enum=False),
        nullable=False,
        doc="New lifecycle status transitioned into",
    )
    changed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User ID who executed the transition (promoter, scrutiny officer, inspector)",
    )
    action: Mapped[str] = mapped_column(
        String(100),
        default="STATUS_CHANGE",
        nullable=False,
        doc="Action name (e.g. CREATE_DRAFT, SUBMIT, START_REVIEW, RAISE_QUERY, RESUBMIT, APPROVE, REJECT)",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Statutory observations, scrutiny notes, or deficiency rationale",
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="status_history",
        lazy="selectin",
    )
    changed_by: Mapped[Optional["User"]] = relationship(
        "User",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<ApplicationStatusHistory app='{self.application_id}' "
            f"from='{self.from_status}' to='{self.to_status}' action='{self.action}'>"
        )
