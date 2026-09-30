"""
Geographical location, industrial park intelligence, and jurisdiction mapping service.
Validates Indian postal codes, state-district hierarchies, industrial development zones (MIDC, GIDC, etc.),
and resolves corresponding regional regulatory authorities (SPCB regional offices, DICs).
"""

from dataclasses import dataclass
import re
from typing import Dict, List, Optional
from app.core.exceptions import ValidationError


@dataclass
class IndustrialPark:
    code: str
    name: str
    state: str
    district: str
    nodal_agency: str  # e.g. MIDC, GIDC, KIADB, RIICO, SIPCOT, UPSIDA
    spcb_regional_office: str
    dic_office: str
    water_supply_available: bool
    effluent_treatment_cetp: bool


# Recognized major industrial parks / estates in India
INDUSTRIAL_PARKS: List[IndustrialPark] = [
    IndustrialPark(
        code="MH-MIDC-CHK",
        name="Chakan Industrial Area",
        state="Maharashtra",
        district="Pune",
        nodal_agency="MIDC",
        spcb_regional_office="MPCB Pune Regional Office",
        dic_office="District Industries Centre, Pune",
        water_supply_available=True,
        effluent_treatment_cetp=True,
    ),
    IndustrialPark(
        code="MH-MIDC-BHO",
        name="Bhosari Industrial Estate",
        state="Maharashtra",
        district="Pune",
        nodal_agency="MIDC",
        spcb_regional_office="MPCB Pune Regional Office",
        dic_office="District Industries Centre, Pune",
        water_supply_available=True,
        effluent_treatment_cetp=True,
    ),
    IndustrialPark(
        code="MH-MIDC-TAL",
        name="Talegaon Electronic Zone",
        state="Maharashtra",
        district="Pune",
        nodal_agency="MIDC",
        spcb_regional_office="MPCB Pune Regional Office",
        dic_office="District Industries Centre, Pune",
        water_supply_available=True,
        effluent_treatment_cetp=False,
    ),
    IndustrialPark(
        code="GJ-GIDC-SAN",
        name="Sanand Industrial Estate",
        state="Gujarat",
        district="Ahmedabad",
        nodal_agency="GIDC",
        spcb_regional_office="GPCB Ahmedabad Regional Office",
        dic_office="District Industries Centre, Ahmedabad",
        water_supply_available=True,
        effluent_treatment_cetp=True,
    ),
    IndustrialPark(
        code="KA-KIADB-PEE",
        name="Peenya Industrial Complex",
        state="Karnataka",
        district="Bengaluru Urban",
        nodal_agency="KIADB",
        spcb_regional_office="KSPCB Bengaluru Urban Office",
        dic_office="District Industries Centre, Bengaluru",
        water_supply_available=True,
        effluent_treatment_cetp=True,
    ),
    IndustrialPark(
        code="TN-SIPCOT-SRI",
        name="SIPCOT Industrial Park Sriperumbudur",
        state="Tamil Nadu",
        district="Kanchipuram",
        nodal_agency="SIPCOT",
        spcb_regional_office="TNPCB Sriperumbudur Office",
        dic_office="District Industries Centre, Kanchipuram",
        water_supply_available=True,
        effluent_treatment_cetp=True,
    ),
    IndustrialPark(
        code="DL-DSIIDC-OKH",
        name="Okhla Industrial Area",
        state="Delhi",
        district="South East Delhi",
        nodal_agency="DSIIDC",
        spcb_regional_office="DPCC Central Office",
        dic_office="DIC Delhi",
        water_supply_available=True,
        effluent_treatment_cetp=True,
    ),
]

# States and representative industrial districts
STATE_DISTRICT_MAP: Dict[str, List[str]] = {
    "Maharashtra": ["Pune", "Thane", "Nashik", "Aurangabad", "Nagpur", "Mumbai", "Palghar", "Raigad", "Kolhapur", "Solapur"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bharuch", "Valsad", "Kutch", "Gandhinagar"],
    "Karnataka": ["Bengaluru Urban", "Bengaluru Rural", "Mysuru", "Belagavi", "Dharwad", "Dakshina Kannada", "Tumakuru"],
    "Tamil Nadu": ["Chennai", "Kanchipuram", "Coimbatore", "Tiruvallur", "Salem", "Tiruchirappalli", "Madurai"],
    "Uttar Pradesh": ["Gautam Buddha Nagar", "Ghaziabad", "Kanpur Nagar", "Lucknow", "Agra", "Varanasi", "Meerut"],
    "Haryana": ["Gurugram", "Faridabad", "Panipat", "Sonipat", "Ambala", "Panchkula", "Yamunanagar"],
    "Delhi": ["New Delhi", "North Delhi", "South Delhi", "West Delhi", "East Delhi", "South East Delhi"],
    "Rajasthan": ["Jaipur", "Alwar", "Bhiwadi", "Jodhpur", "Kota", "Udaipur", "Bhilwara"],
    "Telangana": ["Hyderabad", "Medchal-Malkajgiri", "Rangareddy", "Sangareddy", "Warangal"],
    "Andhra Pradesh": ["Visakhapatnam", "Krishna", "Chittoor", "Tirupati", "Guntur", "Nellore"],
}


def validate_pincode(pincode: str) -> bool:
    """
    Validate Indian Postal Index Number (PIN):
    Must be exactly 6 digits, first digit between 1 and 9 (0 is invalid).
    """
    if not pincode or not re.match(r"^[1-9][0-9]{5}$", pincode.strip()):
        raise ValidationError(
            message=f"Invalid Indian PIN Code '{pincode}'. Must be a 6-digit number starting with digits 1-9.",
            details={"field": "pincode", "value": pincode},
        )
    return True


def validate_geo_coordinates(latitude: Optional[float], longitude: Optional[float]) -> bool:
    """
    Validate that geographic coordinates fall within the boundaries of the Indian subcontinent:
    Latitude: approx 6.0° N to 38.0° N
    Longitude: approx 68.0° E to 98.0° E
    """
    if latitude is not None:
        if not (6.0 <= latitude <= 38.0):
            raise ValidationError(
                message=f"Latitude {latitude}° is outside the Indian geographical bounds (6.0° to 38.0°).",
                details={"field": "latitude", "value": latitude},
            )

    if longitude is not None:
        if not (68.0 <= longitude <= 98.0):
            raise ValidationError(
                message=f"Longitude {longitude}° is outside the Indian geographical bounds (68.0° to 98.0°).",
                details={"field": "longitude", "value": longitude},
            )

    return True


def validate_location_hierarchy(state: str, district: str) -> bool:
    """
    Ensure the specified district belongs to the given state if state is registered in catalog.
    """
    if not state or not district:
        raise ValidationError(
            message="Both state and district are mandatory for industrial location validation.",
            details={"state": state, "district": district},
        )

    matched_state = next((s for s in STATE_DISTRICT_MAP if s.lower() == state.strip().lower()), None)
    if matched_state:
        districts = [d.lower() for d in STATE_DISTRICT_MAP[matched_state]]
        if district.strip().lower() not in districts:
            raise ValidationError(
                message=f"District '{district}' is not recognized in {matched_state}.",
                details={"field": "district", "state": matched_state, "valid_districts": STATE_DISTRICT_MAP[matched_state]},
            )

    return True


def find_matching_industrial_park(query: str, state: Optional[str] = None) -> Optional[IndustrialPark]:
    """
    Fuzzy match industrial park by name or zone code.
    """
    query_clean = query.lower().strip()
    for park in INDUSTRIAL_PARKS:
        if state and park.state.lower() != state.lower():
            continue
        if query_clean in park.name.lower() or query_clean in park.code.lower():
            return park
    return None


def get_regulatory_jurisdiction(state: str, district: str, industrial_area: Optional[str] = None) -> Dict[str, str]:
    """
    Derive the nodal authority, SPCB regional office, and Single Window cell.
    """
    if industrial_area:
        matched_park = find_matching_industrial_park(industrial_area, state)
        if matched_park:
            return {
                "nodal_agency": matched_park.nodal_agency,
                "spcb_regional_office": matched_park.spcb_regional_office,
                "dic_office": matched_park.dic_office,
                "industrial_zone": matched_park.name,
                "cetp_available": str(matched_park.effluent_treatment_cetp),
            }

    # Fallback to District / State generic offices
    return {
        "nodal_agency": f"{state} Industrial Development Corporation",
        "spcb_regional_office": f"{state} Pollution Control Board Regional Office ({district})",
        "dic_office": f"District Industries Centre, {district}",
        "industrial_zone": industrial_area or "Independent Industrial Plot",
        "cetp_available": "False",
    }
