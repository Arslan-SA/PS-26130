"""
Enterprise and Industrial Profile Completeness Evaluation Engine.
Provides granular weighted section scoring, identifies missing mandatory regulatory fields,
and gates approval submission readiness.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from app.models.business import Business
from app.models.business_profile import BusinessProfile


@dataclass
class CompletenessSection:
    name: str
    weight: int
    score: int
    missing_fields: List[str] = field(default_factory=list)


@dataclass
class ProfileCompletenessReport:
    total_score: int
    is_ready_for_approvals: bool
    sections: Dict[str, CompletenessSection]
    missing_mandatory_fields: List[str]
    missing_recommended_fields: List[str]
    actionable_recommendations: List[str]


def evaluate_profile_completeness(
    business: Business,
    profile: Optional[BusinessProfile] = None,
) -> ProfileCompletenessReport:
    """
    Compute weighted completeness score (0-100) across 5 statutory pillars:
    1. Legal Entity Identifiers (25 points)
    2. Manufacturing & Environmental Category (25 points)
    3. Location & Spatial Mapping (25 points)
    4. Capital, Workforce & Utilities (15 points)
    5. Nodal Contact & Representation (10 points)
    """
    missing_mandatory: List[str] = []
    missing_recommended: List[str] = []
    recommendations: List[str] = []

    # --- Pillar 1: Legal Entity Identifiers (25 pts) ---
    p1_score = 0
    p1_missing = []
    if business.legal_name and business.legal_name.strip():
        p1_score += 5
    else:
        p1_missing.append("legal_name")
        missing_mandatory.append("Legal Enterprise Name")

    if business.entity_type:
        p1_score += 5

    if business.pan and len(business.pan.strip()) == 10:
        p1_score += 10
    else:
        p1_missing.append("pan")
        missing_mandatory.append("10-character PAN")

    if business.gstin or business.udyam_number:
        p1_score += 5
    else:
        p1_missing.append("gstin_or_udyam")
        missing_recommended.append("GSTIN or Udyam Registration Number")
        recommendations.append("Add GSTIN or MSME Udyam number to unlock automated single-window tax credits.")

    # --- Pillar 2: Manufacturing & Environmental Category (25 pts) ---
    p2_score = 0
    p2_missing = []
    if profile:
        if profile.nic_code and profile.nic_code.strip():
            p2_score += 5
        else:
            p2_missing.append("nic_code")
            missing_recommended.append("NIC-2008 Classification Code")

        if profile.manufacturing_activity and profile.manufacturing_activity.strip():
            p2_score += 10
        else:
            p2_missing.append("manufacturing_activity")
            missing_mandatory.append("Manufacturing Activity Description")

        if profile.pollution_category:
            p2_score += 10
        else:
            p2_missing.append("pollution_category")
            missing_mandatory.append("CPCB Pollution Category (Red/Orange/Green/White)")
            recommendations.append("Classify industrial pollution category to identify required PCB environmental NOCs.")
    else:
        p2_missing.extend(["nic_code", "manufacturing_activity", "pollution_category"])
        missing_mandatory.extend(["Manufacturing Activity Description", "CPCB Pollution Category"])

    # --- Pillar 3: Location & Spatial Mapping (25 pts) ---
    p3_score = 0
    p3_missing = []
    if profile:
        if profile.state and profile.district:
            p3_score += 10
        else:
            p3_missing.append("state_and_district")
            missing_mandatory.append("Operational State and District")

        if profile.pincode and len(profile.pincode.strip()) == 6:
            p3_score += 5
        else:
            p3_missing.append("pincode")
            missing_mandatory.append("6-digit Postal PIN Code")

        if profile.industrial_area or profile.full_address:
            p3_score += 5
        else:
            p3_missing.append("industrial_area_or_address")
            missing_recommended.append("Industrial Park Name or Full Site Address")

        if profile.latitude is not None and profile.longitude is not None:
            p3_score += 5
        else:
            p3_missing.append("geo_coordinates")
            missing_recommended.append("GPS Geo-Coordinates")
            recommendations.append("Pinpoint physical factory coordinates for automated GIS inspectorate mapping.")
    else:
        p3_missing.extend(["state_and_district", "pincode", "address"])
        missing_mandatory.extend(["Operational State and District", "6-digit PIN Code"])

    # --- Pillar 4: Capital, Workforce & Utilities (15 pts) ---
    p4_score = 0
    p4_missing = []
    if profile:
        if profile.total_employees is not None and profile.total_employees > 0:
            p4_score += 5
        else:
            p4_missing.append("total_employees")
            missing_recommended.append("Total Employee Count")

        if profile.plant_machinery_investment is not None and profile.plant_machinery_investment > 0:
            p4_score += 5
        else:
            p4_missing.append("plant_machinery_investment")
            missing_recommended.append("Plant & Machinery Investment Value")

        if profile.power_requirement_kw is not None or profile.water_requirement_kld is not None:
            p4_score += 5
        else:
            p4_missing.append("utility_demand")
            missing_recommended.append("Connected Electrical Load or Water Requirement")
            recommendations.append("Specify connected power load in kW to calculate DISCOM HT/LT approval requirements.")
    else:
        p4_missing.extend(["total_employees", "investment", "utility_demand"])
        missing_recommended.extend(["Workforce Count", "Capital Investment"])

    # --- Pillar 5: Nodal Contact & Representation (10 pts) ---
    p5_score = 0
    p5_missing = []
    if profile:
        if profile.contact_person and profile.contact_person.strip():
            p5_score += 5
        else:
            p5_missing.append("contact_person")
            missing_mandatory.append("Nodal Representative Contact Person")

        if profile.contact_phone or profile.contact_email:
            p5_score += 5
        else:
            p5_missing.append("contact_phone_or_email")
            missing_mandatory.append("Official Mobile or Email")
    else:
        p5_missing.extend(["contact_person", "contact_phone_or_email"])
        missing_mandatory.append("Nodal Representative Contact Person")

    total_score = p1_score + p2_score + p3_score + p4_score + p5_score
    is_ready = (total_score >= 70) and (len(missing_mandatory) == 0)

    sections = {
        "legal_identity": CompletenessSection("Legal Identity", 25, p1_score, p1_missing),
        "manufacturing_environment": CompletenessSection("Manufacturing & Environment", 25, p2_score, p2_missing),
        "location_spatial": CompletenessSection("Location & Spatial", 25, p3_score, p3_missing),
        "capital_workforce": CompletenessSection("Capital & Workforce", 15, p4_score, p4_missing),
        "nodal_contact": CompletenessSection("Nodal Contact", 10, p5_score, p5_missing),
    }

    return ProfileCompletenessReport(
        total_score=total_score,
        is_ready_for_approvals=is_ready,
        sections=sections,
        missing_mandatory_fields=missing_mandatory,
        missing_recommended_fields=missing_recommended,
        actionable_recommendations=recommendations,
    )
