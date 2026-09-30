"""
CPCB (Central Pollution Control Board) Industrial Classification Engine.
Implements the revised 4-tier categorization (Red, Orange, Green, White) based on
Pollution Index (PI) scoring and NIC-2008 / industrial activity matching.
"""

from dataclasses import dataclass
from typing import Optional
from app.models.business_profile import PollutionCategory


@dataclass
class ClassificationResult:
    category: PollutionCategory
    pollution_index_range: str
    estimated_pi_score: int
    requires_consent_to_establish: bool
    requires_consent_to_operate: bool
    requires_eia: bool
    rationale: str
    regulatory_tier: str


# Reference mapping of high-impact NIC codes & sectors to CPCB categories
CPCB_SECTOR_RULES = [
    # RED CATEGORY (PI >= 60)
    {
        "category": PollutionCategory.RED,
        "pi_min": 60,
        "pi_default": 75,
        "keywords": [
            "chemical", "fertilizer", "pesticide", "refinery", "petrochemical",
            "tannery", "leather tanning", "thermal power", "pulp", "paper mill",
            "dye", "pigment", "hazardous waste", "smelting", "metallurgy",
            "pharmaceutical", "bulk drug", "cement", "distillery", "sugar mill",
            "asbestos", "battery manufacturing", "foundry", "plating", "electroplating"
        ],
        "nic_prefixes": ["201", "202", "191", "192", "241", "242", "210", "170"],
        "rationale": "High pollution potential with significant emissions, effluent, or hazardous waste generation. Requires Consent to Establish (CTE), Consent to Operate (CTO), and potential Environmental Impact Assessment (EIA).",
        "requires_cte": True,
        "requires_cto": True,
        "requires_eia": True,
    },
    # ORANGE CATEGORY (PI 41 to 59)
    {
        "category": PollutionCategory.ORANGE,
        "pi_min": 41,
        "pi_default": 50,
        "keywords": [
            "food processing", "dairy", "bakery", "textile", "weaving", "dyeing",
            "stone crusher", "brick", "glass", "ceramic", "paint formulation",
            "printing ink", "rubber", "plastic molding", "automobile servicing",
            "hotel", "restaurant", "hospital", "meat processing", "saw mill",
            "plywood", "metal fabrication", "heat treatment", "wire drawing"
        ],
        "nic_prefixes": ["101", "102", "103", "104", "105", "106", "107", "131", "221", "222", "231", "239"],
        "rationale": "Moderate pollution potential with regulated emissions or trade effluent. Requires CTE and CTO with statutory pollution control measures.",
        "requires_cte": True,
        "requires_cto": True,
        "requires_eia": False,
    },
    # GREEN CATEGORY (PI 21 to 40)
    {
        "category": PollutionCategory.GREEN,
        "pi_min": 21,
        "pi_default": 30,
        "keywords": [
            "solar panel", "solar cell", "assembly", "electronics assembly", "flour mill",
            "dal mill", "packaging", "corrugated box", "garment", "apparel stitching",
            "leather goods assembly", "dry mechanical", "carpentry", "electrical appliances",
            "biscuit", "confectionery", "cold storage", "warehouse", "tea blending"
        ],
        "nic_prefixes": ["141", "151", "152", "261", "262", "263", "271", "272", "273", "274", "275", "172"],
        "rationale": "Low pollution potential with minimal air or water emissions. Simplified CTE/CTO online consent process with fast-track clearance.",
        "requires_cte": True,
        "requires_cto": True,
        "requires_eia": False,
    },
    # WHITE CATEGORY (PI <= 20)
    {
        "category": PollutionCategory.WHITE,
        "pi_min": 0,
        "pi_default": 15,
        "keywords": [
            "software", "information technology", "it services", "medical oxygen packing",
            "electric vehicle assembly", "ev assembly", "bicycle assembly", "solar power generation",
            "wind power", "dry processing", "handloom", "chalk making", "cotton spinning dry",
            "knitting", "candle", "bio fertilizer", "fly ash brick"
        ],
        "nic_prefixes": ["620", "631", "351", "309"],
        "rationale": "Practically non-polluting industrial activity. Exempted from CTE and CTO consents; only self-intimation to State Pollution Control Board required.",
        "requires_cte": False,
        "requires_cto": False,
        "requires_eia": False,
    },
]


def classify_industry(
    nic_code: Optional[str] = None,
    manufacturing_activity: Optional[str] = None,
    power_kw: Optional[float] = None,
) -> ClassificationResult:
    """
    Classify an enterprise into CPCB Red/Orange/Green/White category.
    Evaluates NIC code, activity descriptions, and power threshold modifiers.
    """
    nic_clean = nic_code.strip() if nic_code else ""
    activity_clean = manufacturing_activity.lower().strip() if manufacturing_activity else ""

    # 1. Match by NIC code prefix (priority)
    if nic_clean:
        for rule in CPCB_SECTOR_RULES:
            for prefix in rule["nic_prefixes"]:
                if nic_clean.startswith(prefix):
                    return ClassificationResult(
                        category=rule["category"],
                        pollution_index_range=f"{rule['pi_min']}+",
                        estimated_pi_score=rule["pi_default"],
                        requires_consent_to_establish=rule["requires_cte"],
                        requires_consent_to_operate=rule["requires_cto"],
                        requires_eia=rule["requires_eia"],
                        rationale=f"Classified under CPCB {rule['category'].value} based on NIC code '{nic_clean}'. {rule['rationale']}",
                        regulatory_tier=f"CPCB-{rule['category'].value}",
                    )

    # 2. Match by Activity keywords (longest matching keyword takes precedence)
    if activity_clean:
        matched_candidates = []
        for rule in CPCB_SECTOR_RULES:
            for keyword in rule["keywords"]:
                if keyword in activity_clean:
                    matched_candidates.append((len(keyword), keyword, rule))
        
        if matched_candidates:
            # Sort descending by length so most specific phrase takes priority
            matched_candidates.sort(key=lambda x: x[0], reverse=True)
            _, best_keyword, best_rule = matched_candidates[0]
            return ClassificationResult(
                category=best_rule["category"],
                pollution_index_range=f"{best_rule['pi_min']}+",
                estimated_pi_score=best_rule["pi_default"],
                requires_consent_to_establish=best_rule["requires_cte"],
                requires_consent_to_operate=best_rule["requires_cto"],
                requires_eia=best_rule["requires_eia"],
                rationale=f"Classified under CPCB {best_rule['category'].value} based on activity keywords '{best_keyword}'. {best_rule['rationale']}",
                regulatory_tier=f"CPCB-{best_rule['category'].value}",
            )

    # 3. Fallback based on connected electrical load if no clear sector match
    if power_kw is not None and power_kw > 500:
        return ClassificationResult(
            category=PollutionCategory.ORANGE,
            pollution_index_range="41-59",
            estimated_pi_score=48,
            requires_consent_to_establish=True,
            requires_consent_to_operate=True,
            requires_eia=False,
            rationale="Defaulted to Orange Category due to high connected electrical load (>500 kW) indicating significant manufacturing machinery.",
            regulatory_tier="CPCB-ORANGE-LOAD-DEFAULT",
        )

    # Default to Green for unclassified light enterprises
    return ClassificationResult(
        category=PollutionCategory.GREEN,
        pollution_index_range="21-40",
        estimated_pi_score=28,
        requires_consent_to_establish=True,
        requires_consent_to_operate=True,
        requires_eia=False,
        rationale="Defaulted to Green Category for standard light manufacturing/services pending department physical verification.",
        regulatory_tier="CPCB-GREEN-DEFAULT",
    )
