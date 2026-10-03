"""
Government Schemes, Subsidies & Eligibility Domain Models (Phase 8, Fragments 103–104).

Provides:
- GovernmentScheme: Catalog of Central & State industrial incentive schemes
  (PMEGP, Mudra, CGTMSE, PLI, Technology Upgradation, ZED, Capital Subsidies).
- SchemeEligibilityRule: Definitive criteria defining eligibility
  (MSME classification, investment, turnover, NIC code sectors, pollution category, location, Udyam).
- SchemeApplication: Industry user scheme tracking, application intent, and milestone status.
"""

from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.business import Business


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SchemeType(str, Enum):
    """Category of financial or regulatory incentive."""
    CAPITAL_SUBSIDY = "CAPITAL_SUBSIDY"
    INTEREST_SUBVENTION = "INTEREST_SUBVENTION"
    CREDIT_GUARANTEE = "CREDIT_GUARANTEE"
    PRODUCTION_LINKED_INCENTIVE = "PRODUCTION_LINKED_INCENTIVE"
    QUALITY_CERTIFICATION = "QUALITY_CERTIFICATION"
    TECHNOLOGY_UPGRADATION = "TECHNOLOGY_UPGRADATION"
    INFRASTRUCTURE_SUPPORT = "INFRASTRUCTURE_SUPPORT"
    GREEN_INCENTIVE = "GREEN_INCENTIVE"
    EXPORT_PROMOTION = "EXPORT_PROMOTION"


class SchemeLevel(str, Enum):
    """Administrative jurisdiction level."""
    CENTRAL = "CENTRAL"
    STATE = "STATE"


class ApplicationMode(str, Enum):
    """How the applicant submits for the scheme."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    HYBRID = "HYBRID"


class SchemeApplicationStatus(str, Enum):
    """Lifecycle stages of an industry unit's scheme application."""
    BOOKMARKED = "BOOKMARKED"               # Saved for evaluation
    PREPARING = "PREPARING"                 # Gathering documents
    APPLIED = "APPLIED"                     # Submitted to nodal agency
    UNDER_SCRUTINY = "UNDER_SCRUTINY"       # Agency evaluating eligibility
    SANCTIONED = "SANCTIONED"               # In-principle approval / Sanction letter issued
    DISBURSED = "DISBURSED"                 # Subsidy/loan credited to escrow/bank account
    REJECTED = "REJECTED"                   # Application rejected
    CANCELLED = "CANCELLED"                 # Withdrawn by applicant


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class GovernmentScheme(BaseModel):
    """
    Catalog of Government Financial & Regulatory Support Schemes.
    Includes Central ministries (MSME, DPIIT, MeitY, Food Processing) and
    State Industrial Development Corporations.
    """
    __tablename__ = "government_schemes"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    short_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    ministry: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    nodal_agency: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    scheme_type: Mapped[SchemeType] = mapped_column(
        SQLEnum(SchemeType, name="scheme_type_enum", native_enum=False),
        nullable=False,
        index=True,
    )
    level: Mapped[SchemeLevel] = mapped_column(
        SQLEnum(SchemeLevel, name="scheme_level_enum", native_enum=False),
        default=SchemeLevel.CENTRAL,
        nullable=False,
        index=True,
    )
    state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    target_beneficiary: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    benefit_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    max_subsidy_amount: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Maximum financial benefit in INR (e.g. 5000000 for 50 Lakhs)",
    )
    subsidy_percentage: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Percentage subsidy of eligible project cost (e.g. 35.0)",
    )
    interest_subsidy_rate: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Annual interest rate subvention in percentage (e.g. 5.0)",
    )
    official_portal_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    application_mode: Mapped[ApplicationMode] = mapped_column(
        SQLEnum(ApplicationMode, name="application_mode_enum", native_enum=False),
        default=ApplicationMode.ONLINE,
        nullable=False,
    )
    guidance_steps: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        doc="Structured step-by-step guidance instructions for application",
    )
    required_document_codes: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        doc="Document Vault type codes required (e.g. ['PAN_CARD', 'UDYAM_CERTIFICATE'])",
    )
    tags: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Relationships
    rule: Mapped[Optional["SchemeEligibilityRule"]] = relationship(
        "SchemeEligibilityRule",
        back_populates="scheme",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    applications: Mapped[List["SchemeApplication"]] = relationship(
        "SchemeApplication",
        back_populates="scheme",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["scheme_type"] = self.scheme_type.value if hasattr(self.scheme_type, "value") else str(self.scheme_type)
        data["level"] = self.level.value if hasattr(self.level, "value") else str(self.level)
        data["application_mode"] = self.application_mode.value if hasattr(self.application_mode, "value") else str(self.application_mode)
        if "rule" in self.__dict__ and self.__dict__["rule"]:
            data["rule"] = self.__dict__["rule"].to_dict()
        return data


class SchemeEligibilityRule(BaseModel):
    """
    Parametric eligibility rule set used by the AI/Rule matching engine
    to score and rank suitability for an industrial unit.
    """
    __tablename__ = "scheme_eligibility_rules"

    scheme_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("government_schemes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Investment Thresholds (in INR)
    min_investment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_investment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Annual Turnover Thresholds (in INR)
    min_turnover: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_turnover: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Allowed MSME Categories (e.g., ["MICRO", "SMALL"])
    allowed_msme_categories: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Allowed Entity Legal Types (e.g., ["PRIVATE_LIMITED", "LLP", "PROPRIETORSHIP"])
    allowed_entity_types: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Allowed 2-digit or 4-digit NIC codes (empty means all industrial sectors)
    allowed_sectors_nic: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Allowed CPCB Pollution Categories (e.g. ["WHITE", "GREEN", "ORANGE", "RED"])
    allowed_pollution_categories: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Allowed States (empty means all India)
    allowed_states: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Special Criteria
    requires_udyam: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    requires_women_ownership: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    min_employees: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    max_firm_age_years: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    min_score_threshold: Mapped[float] = mapped_column(
        Float,
        default=50.0,
        nullable=False,
    )

    # Relationship
    scheme: Mapped["GovernmentScheme"] = relationship(
        "GovernmentScheme",
        back_populates="rule",
    )

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


class SchemeApplication(BaseModel):
    """
    Tracks an enterprise's engagement, readiness assessment,
    and progress applying for a government scheme.
    """
    __tablename__ = "scheme_applications"

    business_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheme_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("government_schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[SchemeApplicationStatus] = mapped_column(
        SQLEnum(SchemeApplicationStatus, name="scheme_application_status_enum", native_enum=False),
        default=SchemeApplicationStatus.BOOKMARKED,
        nullable=False,
        index=True,
    )
    match_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    applied_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    sanctioned_amount: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    application_reference_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    missing_documents: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business",
        lazy="selectin",
    )
    scheme: Mapped["GovernmentScheme"] = relationship(
        "GovernmentScheme",
        back_populates="applications",
        lazy="selectin",
    )

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["status"] = self.status.value if hasattr(self.status, "value") else str(self.status)
        if self.applied_date:
            data["applied_date"] = self.applied_date.isoformat()
        if "scheme" in self.__dict__ and self.__dict__["scheme"]:
            scheme = self.__dict__["scheme"]
            data["scheme_code"] = scheme.code
            data["scheme_name"] = scheme.name
            data["ministry"] = scheme.ministry
            data["max_subsidy_amount"] = scheme.max_subsidy_amount
        return data
