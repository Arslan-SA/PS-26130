"""
Business database model representing registered industrial enterprises,
MSMEs, corporate entities, and manufacturing firms.
"""

from datetime import date
import enum
from sqlalchemy import Boolean, Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class EntityType(str, enum.Enum):
    """Statutory legal entity constitution types under Indian corporate law."""
    PRIVATE_LIMITED = "PRIVATE_LIMITED"
    PUBLIC_LIMITED = "PUBLIC_LIMITED"
    LLP = "LLP"
    PARTNERSHIP = "PARTNERSHIP"
    PROPRIETORSHIP = "PROPRIETORSHIP"
    ONE_PERSON_COMPANY = "ONE_PERSON_COMPANY"
    TRUST_SOCIETY = "TRUST_SOCIETY"
    PSU = "PSU"


class MSMECategory(str, enum.Enum):
    """
    MSME classification based on statutory composite criteria
    (Investment in Plant & Machinery + Annual Turnover).
    """
    MICRO = "MICRO"      # Investment <= 1 Cr & Turnover <= 5 Cr
    SMALL = "SMALL"      # Investment <= 10 Cr & Turnover <= 50 Cr
    MEDIUM = "MEDIUM"    # Investment <= 50 Cr & Turnover <= 250 Cr
    LARGE = "LARGE"      # Investment > 50 Cr or Turnover > 250 Cr


class Business(BaseModel):
    """
    Industrial enterprise legal entity holding statutory corporate identifiers,
    tax credentials, and regulatory ownership.
    """
    __tablename__ = "businesses"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    legal_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    trade_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type_enum", native_enum=False),
        default=EntityType.PRIVATE_LIMITED,
        nullable=False,
    )
    pan: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )
    gstin: Mapped[str | None] = mapped_column(
        String(15),
        nullable=True,
        index=True,
    )
    udyam_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        index=True,
    )
    cin: Mapped[str | None] = mapped_column(
        String(21),
        nullable=True,
        index=True,
    )
    msme_category: Mapped[MSMECategory] = mapped_column(
        Enum(MSMECategory, name="msme_category_enum", native_enum=False),
        default=MSMECategory.MICRO,
        nullable=False,
        index=True,
    )
    incorporation_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="businesses", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Business id={self.id} legal_name='{self.legal_name}' pan='{self.pan}'>"
