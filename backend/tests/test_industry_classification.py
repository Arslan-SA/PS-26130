"""
Unit tests for CPCB Red/Orange/Green/White Industrial Classification Engine.
"""

import pytest
from app.models.business_profile import PollutionCategory
from app.services.classification_service import classify_industry


def test_classify_red_category():
    """Verify high-impact polluting industries classified under RED category."""
    # Chemical synthesis via NIC prefix 201
    res1 = classify_industry(nic_code="20111", manufacturing_activity="Manufacture of basic industrial chemicals")
    assert res1.category == PollutionCategory.RED
    assert res1.estimated_pi_score >= 60
    assert res1.requires_consent_to_establish is True
    assert res1.requires_consent_to_operate is True
    assert res1.requires_eia is True

    # Pharmaceutical bulk drug via keyword
    res2 = classify_industry(manufacturing_activity="Active Pharmaceutical Ingredients (bulk drug) and formulating antibiotics")
    assert res2.category == PollutionCategory.RED
    assert res2.requires_consent_to_establish is True


def test_classify_orange_category():
    """Verify moderately polluting industries classified under ORANGE category."""
    # Food processing via NIC prefix 107
    res1 = classify_industry(nic_code="10799", manufacturing_activity="Manufacture of other food products")
    assert res1.category == PollutionCategory.ORANGE
    assert 41 <= res1.estimated_pi_score <= 59
    assert res1.requires_consent_to_establish is True
    assert res1.requires_eia is False

    # Stone crushing via keyword
    res2 = classify_industry(manufacturing_activity="Quarrying and stone crusher operations")
    assert res2.category == PollutionCategory.ORANGE


def test_classify_green_category():
    """Verify low pollution industries classified under GREEN category."""
    # Solar panel assembly
    res1 = classify_industry(nic_code="27101", manufacturing_activity="Solar panel assembly and installation components")
    assert res1.category == PollutionCategory.GREEN
    assert 21 <= res1.estimated_pi_score <= 40
    assert res1.requires_consent_to_establish is True
    assert res1.requires_eia is False

    # Garment stitching
    res2 = classify_industry(manufacturing_activity="Apparel stitching and ready-made garment packaging")
    assert res2.category == PollutionCategory.GREEN


def test_classify_white_category():
    """Verify practically non-polluting industries classified under WHITE category."""
    # Software IT services via NIC prefix 620
    res1 = classify_industry(nic_code="62010", manufacturing_activity="Software publishing and enterprise IT consulting")
    assert res1.category == PollutionCategory.WHITE
    assert res1.estimated_pi_score <= 20
    assert res1.requires_consent_to_establish is False
    assert res1.requires_consent_to_operate is False

    # EV assembly via keyword
    res2 = classify_industry(manufacturing_activity="Electric vehicle assembly of light scooters without painting")
    assert res2.category == PollutionCategory.WHITE
    assert res2.requires_consent_to_establish is False


def test_classify_fallback_and_power_load():
    """Verify power load heuristic overrides unclassified lightweight industries."""
    # Heavy electrical power demand without matching keywords
    res = classify_industry(
        manufacturing_activity="Specialized precision machinery testing",
        power_kw=750.0,
    )
    assert res.category == PollutionCategory.ORANGE
    assert res.requires_consent_to_establish is True

    # Generic unclassified activity
    default_res = classify_industry(manufacturing_activity="General warehouse storage and distribution")
    assert default_res.category == PollutionCategory.GREEN
