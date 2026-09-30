"""
BusinessProfile model representing operational details of an industrial unit:
manufacturing activity, NIC classification, location, workforce, and contact.
"""

import enum
from sqlalchemy import (
    Boolean, Enum, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class IndustryScale(str, enum.Enum):
    """Operational scale classification for the industrial unit."""
    COTTAGE = "COTTAGE"
    SMALL_SCALE = "SMALL_SCALE"
    MEDIUM_SCALE = "MEDIUM_SCALE"
    LARGE_SCALE = "LARGE_SCALE"
    MEGA = "MEGA"


class PollutionCategory(str, enum.Enum):
    """
    CPCB pollution classification for industrial units.
    Determines the set of environmental clearances required.
    """
    RED = "RED"
    ORANGE = "ORANGE"
    GREEN = "GREEN"
    WHITE = "WHITE"


class BusinessProfile(BaseModel):
    """
    Operational profile of an industrial unit — manufacturing activity,
    location, workforce, investment, and environmental classification.
    """
    __tablename__ = "business_profiles"

    business_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # --- Manufacturing Activity ---
    nic_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True,
    )
    manufacturing_activity: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    products_services: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    industry_scale: Mapped[IndustryScale] = mapped_column(
        Enum(IndustryScale, name="industry_scale_enum", native_enum=False),
        default=IndustryScale.SMALL_SCALE,
        nullable=False,
    )
    pollution_category: Mapped[PollutionCategory | None] = mapped_column(
        Enum(PollutionCategory, name="pollution_category_enum", native_enum=False),
        nullable=True,
        index=True,
    )

    # --- Location ---
    state: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(6), nullable=True, index=True)
    full_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    plot_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    industrial_area: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Workforce & Investment ---
    total_employees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plant_machinery_investment: Mapped[float | None] = mapped_column(Float, nullable=True)
    land_area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    annual_turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_requirement_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_requirement_kld: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Contact ---
    contact_person: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Completeness ---
    profile_completeness: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_profile_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    business = relationship("Business", back_populates="profile", lazy="selectin")

    def __init__(self, **kwargs):
        kwargs.setdefault("industry_scale", IndustryScale.SMALL_SCALE)
        kwargs.setdefault("profile_completeness", 0)
        kwargs.setdefault("is_profile_complete", False)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<BusinessProfile business_id={self.business_id} nic={self.nic_code}>"
