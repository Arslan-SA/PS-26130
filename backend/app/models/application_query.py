"""
Application Query / Deficiency domain model (Fragment 83).
Allows department scrutiny officers to flag document-level or field-level deficiencies,
and enables industrial applicants to submit corrective clarifications and replacement files.
"""

from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.document import Document
    from app.models.user import User


class QueryStatus(str, Enum):
    """Lifecycle status of a deficiency query."""
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    WAIVED = "WAIVED"


class ApplicationQuery(BaseModel):
    """
    Deficiency notice or clarification request raised by a scrutiny officer
    against an application or specific uploaded document.
    """
    __tablename__ = "application_queries"

    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target clearance application under scrutiny",
    )
    raised_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Scrutiny officer user ID who issued the deficiency notice",
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional reference to deficient document requiring re-upload/clarification",
    )
    query_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Short description of deficiency (e.g. Incomplete Site Plan layout)",
    )
    query_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Detailed statutory deficiency remarks and instructions for compliance",
    )
    status: Mapped[QueryStatus] = mapped_column(
        SQLEnum(QueryStatus, name="query_status_enum", native_enum=False),
        default=QueryStatus.OPEN,
        nullable=False,
        index=True,
        doc="Deficiency resolution status",
    )
    due_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Applicant deadline to respond before application gets flagged",
    )
    response_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Applicant's corrective explanation or clarification",
    )
    response_document_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Replacement or supporting document uploaded by applicant",
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when query was resolved",
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="queries",
        lazy="selectin",
    )
    raised_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[raised_by_user_id],
        lazy="selectin",
    )
    document: Mapped[Optional["Document"]] = relationship(
        "Document",
        foreign_keys=[document_id],
        lazy="selectin",
    )
    response_document: Mapped[Optional["Document"]] = relationship(
        "Document",
        foreign_keys=[response_document_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ApplicationQuery id='{self.id}' app='{self.application_id}' status='{self.status.value}'>"
