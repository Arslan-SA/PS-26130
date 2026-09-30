"""
Indian Statutory Document and Identification Validation Service.
Implements format verification, structural rules, and cross-field statutory checks for:
- PAN (Permanent Account Number - CBDT / Income Tax)
- GSTIN (Goods and Services Tax Identification Number - GSTN)
- CIN (Corporate Identification Number - Ministry of Corporate Affairs)
- Udyam (MSME Registration Number - Ministry of MSME)
"""

from datetime import date
import re
from typing import Optional
from app.core.exceptions import ValidationError
from app.models.business import EntityType

# GST State Codes mapping (first 2 digits of GSTIN)
GST_STATE_CODES = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "36": "Telangana",
    "37": "Andhra Pradesh",
}

PAN_REGEX = re.compile(r"^[A-Z]{3}[ABCFGHLJPT][A-Z][0-9]{4}[A-Z]$")
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
CIN_REGEX = re.compile(r"^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$")
UDYAM_REGEX = re.compile(r"^UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}$")


def validate_pan(pan: str, entity_type: Optional[EntityType] = None) -> bool:
    """
    Validate 10-character alphanumeric PAN format and 4th character entity alignment:
    - C: Company (Private / Public Limited)
    - F: Partnership Firm / LLP
    - P: Proprietorship / Individual
    - T: Trust
    """
    pan_clean = pan.upper().strip()
    if not PAN_REGEX.match(pan_clean):
        raise ValidationError(
            message=f"Invalid PAN format '{pan_clean}'. Must be 10 characters (5 letters, 4 numbers, 1 letter).",
            details={"field": "pan", "value": pan_clean},
        )

    entity_char = pan_clean[3]
    if entity_type:
        if entity_type in (EntityType.PRIVATE_LIMITED, EntityType.PUBLIC_LIMITED):
            if entity_char != "C":
                raise ValidationError(
                    message=f"PAN '{pan_clean}' indicates entity status '{entity_char}', but enterprise is registered as Company (expects 'C').",
                    details={"field": "pan", "expected_character": "C", "actual": entity_char},
                )
        elif entity_type in (EntityType.PARTNERSHIP, EntityType.LLP):
            if entity_char != "F":
                raise ValidationError(
                    message=f"PAN '{pan_clean}' indicates status '{entity_char}', but entity is Partnership/LLP (expects 'F').",
                    details={"field": "pan", "expected_character": "F", "actual": entity_char},
                )
        elif entity_type == EntityType.PROPRIETORSHIP:
            if entity_char != "P":
                raise ValidationError(
                    message=f"PAN '{pan_clean}' indicates status '{entity_char}', but entity is Sole Proprietorship (expects individual 'P').",
                    details={"field": "pan", "expected_character": "P", "actual": entity_char},
                )

    return True


def validate_gstin(gstin: str, pan: Optional[str] = None, state: Optional[str] = None) -> bool:
    """
    Validate 15-character GSTIN format, matching PAN, and registered State code.
    """
    gstin_clean = gstin.upper().strip()
    if not GSTIN_REGEX.match(gstin_clean):
        raise ValidationError(
            message=f"Invalid GSTIN format '{gstin_clean}'. Must be 15 characters conforming to GSTN standard.",
            details={"field": "gstin", "value": gstin_clean},
        )

    state_code = gstin_clean[:2]
    if state_code not in GST_STATE_CODES:
        raise ValidationError(
            message=f"GSTIN state code '{state_code}' is not a valid Indian GST state code.",
            details={"field": "gstin", "state_code": state_code},
        )

    # Cross-validate PAN embedded in GSTIN
    if pan:
        pan_clean = pan.upper().strip()
        gstin_pan = gstin_clean[2:12]
        if gstin_pan != pan_clean:
            raise ValidationError(
                message=f"GSTIN '{gstin_clean}' contains PAN '{gstin_pan}' which does not match enterprise PAN '{pan_clean}'.",
                details={"field": "gstin", "gstin_pan": gstin_pan, "business_pan": pan_clean},
            )

    # Cross-validate State name if given
    if state:
        expected_state = GST_STATE_CODES[state_code]
        if expected_state.lower() != state.strip().lower():
            raise ValidationError(
                message=f"GSTIN prefix '{state_code}' corresponds to {expected_state}, but enterprise is registered in {state}.",
                details={"field": "gstin", "gst_state": expected_state, "business_state": state},
            )

    return True


def validate_cin(
    cin: str,
    entity_type: Optional[EntityType] = None,
    incorporation_date: Optional[date] = None,
) -> bool:
    """
    Validate 21-character MCA Corporate Identification Number (CIN).
    Verifies company type code (PTC, PLC, etc.) and incorporation year.
    """
    cin_clean = cin.upper().strip()
    if not CIN_REGEX.match(cin_clean):
        raise ValidationError(
            message=f"Invalid CIN format '{cin_clean}'. Must be 21 characters conforming to MCA standard (e.g., U27100MH2020PTC123456).",
            details={"field": "cin", "value": cin_clean},
        )

    # Extract components
    corp_type = cin_clean[12:15]
    incorp_year = int(cin_clean[8:12])

    if entity_type == EntityType.PRIVATE_LIMITED and corp_type != "PTC":
        raise ValidationError(
            message=f"CIN indicates company type '{corp_type}', but entity is Private Limited (expects 'PTC').",
            details={"field": "cin", "expected": "PTC", "actual": corp_type},
        )
    elif entity_type == EntityType.PUBLIC_LIMITED and corp_type != "PLC":
        raise ValidationError(
            message=f"CIN indicates company type '{corp_type}', but entity is Public Limited (expects 'PLC').",
            details={"field": "cin", "expected": "PLC", "actual": corp_type},
        )

    if incorporation_date and incorporation_date.year != incorp_year:
        raise ValidationError(
            message=f"CIN incorporation year '{incorp_year}' does not match date of incorporation year '{incorporation_date.year}'.",
            details={"field": "cin", "cin_year": incorp_year, "incorporation_year": incorporation_date.year},
        )

    return True


def validate_udyam_number(udyam_number: str) -> bool:
    """
    Validate MSME Udyam Registration Number format: UDYAM-XX-00-0000000
    """
    udyam_clean = udyam_number.upper().strip()
    if not UDYAM_REGEX.match(udyam_clean):
        raise ValidationError(
            message=f"Invalid Udyam Number '{udyam_clean}'. Format must be 'UDYAM-ST-DD-NNNNNNN' (e.g. UDYAM-MH-01-0012345).",
            details={"field": "udyam_number", "value": udyam_clean},
        )
    return True
