"""
Tests for Profile Completeness Evaluation Engine, Weighted Scoring, and Approval Readiness Gating.
"""

import pytest
from app.models.business import Business, EntityType, MSMECategory
from app.models.business_profile import BusinessProfile, IndustryScale, PollutionCategory
from app.services.completeness_service import evaluate_profile_completeness


def test_full_profile_100_percent():
    """Verify fully populated profile scores 100% and is ready for approvals."""
    business = Business(
        user_id="user-123",
        legal_name="Apex Precision Engineering Pvt Ltd",
        trade_name="Apex Precision",
        entity_type=EntityType.PRIVATE_LIMITED,
        pan="AAACB1234D",
        gstin="27AAACB1234D1Z5",
        udyam_number="UDYAM-MH-01-0012345",
        msme_category=MSMECategory.SMALL,
    )

    profile = BusinessProfile(
        business_id=business.id,
        nic_code="28190",
        manufacturing_activity="Manufacture of specialized industrial machinery and components",
        products_services="Industrial pumps, valves, CNC parts",
        industry_scale=IndustryScale.SMALL_SCALE,
        pollution_category=PollutionCategory.GREEN,
        state="Maharashtra",
        district="Pune",
        city="Pune",
        pincode="411018",
        full_address="Plot 12, Bhosari MIDC, Pune",
        industrial_area="Bhosari MIDC",
        latitude=18.62,
        longitude=73.84,
        total_employees=45,
        plant_machinery_investment=35000000.0,
        annual_turnover=80000000.0,
        power_requirement_kw=150.0,
        water_requirement_kld=10.0,
        contact_person="Rajesh Patil",
        contact_phone="+919876543210",
        contact_email="rajesh@apexprecision.com",
    )

    report = evaluate_profile_completeness(business, profile)

    assert report.total_score == 100
    assert report.is_ready_for_approvals is True
    assert len(report.missing_mandatory_fields) == 0
    assert report.sections["legal_identity"].score == 25
    assert report.sections["manufacturing_environment"].score == 25
    assert report.sections["location_spatial"].score == 25
    assert report.sections["capital_workforce"].score == 15
    assert report.sections["nodal_contact"].score == 10


def test_sparse_profile_completeness():
    """Verify minimal business profile has lower score and identifies missing mandatory fields."""
    business = Business(
        user_id="user-456",
        legal_name="Newco Traders",
        entity_type=EntityType.PROPRIETORSHIP,
        pan="ABCDE1234F",
    )

    # Empty profile
    report = evaluate_profile_completeness(business, profile=None)

    # Legal entity score: legal_name (5) + entity_type (5) + pan (10) = 20 pts
    assert report.total_score == 20
    assert report.is_ready_for_approvals is False
    assert "Manufacturing Activity Description" in report.missing_mandatory_fields
    assert "Operational State and District" in report.missing_mandatory_fields
    assert "CPCB Pollution Category" in report.missing_mandatory_fields
    assert len(report.actionable_recommendations) > 0


def test_high_score_missing_mandatory_field_gated():
    """Verify profile with score >= 70 but missing a mandatory field is NOT ready for approvals."""
    business = Business(
        user_id="user-789",
        legal_name="ChemTech Labs Pvt Ltd",
        entity_type=EntityType.PRIVATE_LIMITED,
        pan="AABCC9999K",
        gstin="27AABCC9999K1Z0",
    )

    # Missing CPCB pollution category (mandatory)
    profile = BusinessProfile(
        business_id=business.id,
        nic_code="20111",
        manufacturing_activity="Chemical testing and formulation",
        pollution_category=None,  # Missing!
        state="Maharashtra",
        district="Thane",
        pincode="400601",
        industrial_area="Wagle Estate",
        total_employees=30,
        plant_machinery_investment=20000000.0,
        power_requirement_kw=100.0,
        contact_person="Dr. Arvind Varma",
        contact_phone="+919811223344",
    )

    report = evaluate_profile_completeness(business, profile)

    assert report.total_score >= 70
    # Because pollution_category is mandatory, is_ready_for_approvals must be False
    assert report.is_ready_for_approvals is False
    assert any("Pollution Category" in f for f in report.missing_mandatory_fields)
