"""
Tests for Statutory Format and Cross-Field Checksum Validators (PAN, GSTIN, CIN, Udyam).
"""

from datetime import date
import pytest
from app.core.exceptions import ValidationError
from app.models.business import EntityType
from app.services.validation_service import (
    validate_cin,
    validate_gstin,
    validate_pan,
    validate_udyam_number,
)


def test_pan_valid_and_entity_type():
    """Verify PAN validation and 4th character entity alignment."""
    # Private limited company requires 'C'
    assert validate_pan("AAACB1234D", entity_type=EntityType.PRIVATE_LIMITED) is True

    # Partnership / LLP requires 'F'
    assert validate_pan("AAAFB1234D", entity_type=EntityType.PARTNERSHIP) is True
    assert validate_pan("AAAFB1234D", entity_type=EntityType.LLP) is True

    # Sole proprietorship requires 'P'
    assert validate_pan("AAAPB1234D", entity_type=EntityType.PROPRIETORSHIP) is True

    # Mismatch between entity type and PAN 4th character
    with pytest.raises(ValidationError) as exc_info:
        validate_pan("AAAPB1234D", entity_type=EntityType.PRIVATE_LIMITED)
    assert "expects 'C'" in str(exc_info.value.message)

    # Malformed PAN
    with pytest.raises(ValidationError):
        validate_pan("INVALID_PAN")


def test_gstin_format_and_cross_pan():
    """Verify GSTIN format, valid state codes, and PAN matching."""
    pan = "AAACB1234D"
    gstin = "27AAACB1234D1Z5"

    # Valid GSTIN matching PAN and state Maharashtra (27)
    assert validate_gstin(gstin, pan=pan, state="Maharashtra") is True

    # PAN mismatch within GSTIN
    with pytest.raises(ValidationError) as exc_info:
        validate_gstin(gstin, pan="BBBCB1234D")
    assert "does not match enterprise PAN" in str(exc_info.value.message)

    # State mismatch
    with pytest.raises(ValidationError) as exc_info:
        validate_gstin(gstin, pan=pan, state="Gujarat")
    assert "corresponds to Maharashtra" in str(exc_info.value.message)

    # Invalid state code
    with pytest.raises(ValidationError):
        validate_gstin("99AAACB1234D1Z5")


def test_cin_format_and_incorporation_year():
    """Verify CIN format, company type (PTC/PLC), and year alignment."""
    cin = "U27100MH2020PTC123456"

    # Valid Private Limited company incorporated in 2020
    assert validate_cin(
        cin,
        entity_type=EntityType.PRIVATE_LIMITED,
        incorporation_date=date(2020, 5, 20),
    ) is True

    # Company type mismatch (PTC vs Public Limited)
    with pytest.raises(ValidationError) as exc_info:
        validate_cin(cin, entity_type=EntityType.PUBLIC_LIMITED)
    assert "expects 'PLC'" in str(exc_info.value.message)

    # Incorporation year mismatch
    with pytest.raises(ValidationError) as exc_info:
        validate_cin(cin, incorporation_date=date(2018, 1, 1))
    assert "does not match date of incorporation year" in str(exc_info.value.message)


def test_udyam_registration_number():
    """Verify MSME Udyam registration number standard format."""
    # Valid Udyam number
    assert validate_udyam_number("UDYAM-MH-01-0012345") is True
    assert validate_udyam_number("UDYAM-GJ-02-0098765") is True

    # Invalid Udyam numbers
    with pytest.raises(ValidationError):
        validate_udyam_number("UDYAM-12345")

    with pytest.raises(ValidationError):
        validate_udyam_number("MH-01-0012345")
