"""
Document Intelligence Domain Model (Fragment 59).
Stores enterprise regulatory documents, storage paths, file hashes,
OCR extraction payloads, and statutory verification lifecycle states.
"""

from datetime import date
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import Date, Enum as SQLEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.approval_requirement import ApprovalRequirement
    from app.models.business import Business
    from app.models.user import User


class DocumentType(str, Enum):
    """Statutory enterprise document taxonomy."""
    PAN_CARD = "PAN_CARD"
    GST_CERTIFICATE = "GST_CERTIFICATE"
    UDYAM_REGISTRATION = "UDYAM_REGISTRATION"
    LAND_DEED_OR_LEASE = "LAND_DEED_OR_LEASE"
    SITE_PLAN_LAYOUT = "SITE_PLAN_LAYOUT"
    PROJECT_REPORT_DPR = "PROJECT_REPORT_DPR"
    ENVIRONMENTAL_MANAGEMENT_PLAN = "ENVIRONMENTAL_MANAGEMENT_PLAN"
    WATER_BALANCE_CHART = "WATER_BALANCE_CHART"
    POWER_SANCTION_LETTER = "POWER_SANCTION_LETTER"
    FIRE_SAFETY_PLAN = "FIRE_SAFETY_PLAN"
    FACTORY_BUILDING_PLAN = "FACTORY_BUILDING_PLAN"
    CERTIFICATE_OF_INCORPORATION = "CERTIFICATE_OF_INCORPORATION"
    OTHER = "OTHER"


class DocumentVerificationStatus(str, Enum):
    """Lifecycle verification state of an uploaded industrial document."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    VERIFIED = "VERIFIED"
    FLAGGED = "FLAGGED"
    REJECTED = "REJECTED"


class Document(BaseModel):
    """
    Industrial statutory document record storing storage metadata, integrity hash,
    OCR text extraction, and verification status.
    """
    __tablename__ = "documents"

    business_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target enterprise business unit owning this document",
    )
    uploaded_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User ID of the promoter or officer who uploaded the file",
    )
    requirement_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("approval_requirements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional link to a specific statutory approval requirement",
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType, name="document_type_enum"),
        default=DocumentType.OTHER,
        nullable=False,
        index=True,
        doc="Categorical classification of the regulatory document",
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Original uploaded file name",
    )
    storage_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        unique=True,
        doc="Relative physical or object storage path",
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Validated MIME content type (e.g. application/pdf, image/png)",
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="File size in bytes",
    )
    sha256_checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="SHA-256 cryptographic digest for integrity verification",
    )
    verification_status: Mapped[DocumentVerificationStatus] = mapped_column(
        SQLEnum(DocumentVerificationStatus, name="document_verification_status_enum"),
        default=DocumentVerificationStatus.PENDING,
        nullable=False,
        index=True,
        doc="Current automated or officer verification state",
    )
    ocr_raw_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Extracted full raw text from OCR / layout parsing",
    )
    extracted_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        doc="Structured extracted key-value parameters (PAN, dates, numbers)",
    )
    deficiency_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Deficiency queries or remarks raised during automated or manual review",
    )
    issue_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Extracted or declared document issue date",
    )
    expiry_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Extracted or declared document validity expiry date",
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        backref="documents",
        lazy="selectin",
    )
    uploaded_by: Mapped[Optional["User"]] = relationship(
        "User",
        lazy="selectin",
    )
    requirement: Mapped[Optional["ApprovalRequirement"]] = relationship(
        "ApprovalRequirement",
        backref="documents",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Document id='{self.id}' name='{self.file_name}' "
            f"type='{self.document_type}' status='{self.verification_status}'>"
        )
