"""
Tests for Location Information, PIN Validation, and Industrial Park Jurisdiction Mapping.
"""

import pytest
from app.core.exceptions import ValidationError
from app.services.location_service import (
    find_matching_industrial_park,
    get_regulatory_jurisdiction,
    validate_geo_coordinates,
    validate_location_hierarchy,
    validate_pincode,
)


def test_pincode_validation():
    """Verify 6-digit Indian PIN code constraints."""
    # Valid pincodes
    assert validate_pincode("411001") is True
    assert validate_pincode("110001") is True
    assert validate_pincode("560058") is True

    # Invalid pincodes (letters, wrong length, starting with 0)
    with pytest.raises(ValidationError):
        validate_pincode("011001")  # First digit cannot be 0

    with pytest.raises(ValidationError):
        validate_pincode("41100")  # 5 digits

    with pytest.raises(ValidationError):
        validate_pincode("4110019")  # 7 digits

    with pytest.raises(ValidationError):
        validate_pincode("ABC123")


def test_geo_coordinate_boundaries():
    """Verify latitude and longitude coordinates stay within India's bounds."""
    # Valid coordinates (Pune, Chakan MIDC)
    assert validate_geo_coordinates(18.76, 73.85) is True

    # Valid coordinates (Delhi)
    assert validate_geo_coordinates(28.61, 77.20) is True

    # Invalid latitude (beyond Indian boundaries)
    with pytest.raises(ValidationError):
        validate_geo_coordinates(52.52, 73.85)  # Europe latitude

    # Invalid longitude
    with pytest.raises(ValidationError):
        validate_geo_coordinates(18.76, 120.0)  # East Asia longitude


def test_location_state_district_hierarchy():
    """Verify district belongs to state."""
    # Valid pairing
    assert validate_location_hierarchy("Maharashtra", "Pune") is True
    assert validate_location_hierarchy("Gujarat", "Ahmedabad") is True

    # Invalid district for state
    with pytest.raises(ValidationError) as exc_info:
        validate_location_hierarchy("Maharashtra", "Ahmedabad")
    assert "not recognized" in str(exc_info.value.message)


def test_industrial_park_lookup_and_jurisdiction():
    """Verify industrial park matching and automatic SPCB / DIC jurisdiction resolution."""
    # Park lookup
    park = find_matching_industrial_park("Bhosari", state="Maharashtra")
    assert park is not None
    assert park.code == "MH-MIDC-BHO"
    assert park.nodal_agency == "MIDC"
    assert park.effluent_treatment_cetp is True

    # Jurisdiction mapping for known park
    jurisdiction = get_regulatory_jurisdiction("Maharashtra", "Pune", "Bhosari Industrial Estate")
    assert jurisdiction["nodal_agency"] == "MIDC"
    assert "MPCB Pune" in jurisdiction["spcb_regional_office"]
    assert jurisdiction["cetp_available"] == "True"

    # Jurisdiction fallback for unknown plot
    fallback = get_regulatory_jurisdiction("Maharashtra", "Nashik", "Independent Farm Plot")
    assert "Maharashtra Industrial Development Corporation" in fallback["nodal_agency"]
    assert "Nashik" in fallback["spcb_regional_office"]
