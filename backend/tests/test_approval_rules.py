"""
Unit tests for Statutory Regulatory Rules Engine (Fragment 44).
Verifies deterministic clearance triggers, pollution exemptions, threshold logic, and fee formulas.
"""

from app.models.approval_requirement import RequirementStage
from app.models.business_profile import BusinessProfile, IndustryScale, PollutionCategory
from app.services.approval_rules import evaluate_approval_rules


def test_red_category_heavy_industrial_clearances():
    """Verify that a large Red-category chemical plant triggers all major statutory clearances."""
    profile = BusinessProfile(
        business_id="mock-business-id-001",
        manufacturing_activity="Chemical synthesis and industrial paint manufacturing",
        industry_scale=IndustryScale.LARGE_SCALE,
        pollution_category=PollutionCategory.RED,
        land_area_sqm=5000.0,
        total_employees=120,
        plant_machinery_investment=150000000.0,  # 15 Cr (> 10 Cr tier)
        power_requirement_kw=350.0,             # > 50 kW
        water_requirement_kld=45.0,             # >= 10 KLD
    )

    results = evaluate_approval_rules(profile)
    codes = {r.approval_code for r in results}

    assert "CTE_PCB" in codes
    assert "CTO_PCB" in codes
    assert "FIRE_NOC" in codes
    assert "POWER_HT" in codes
    assert "FACTORY_LIC" in codes
    assert "CGWA_GW" in codes

    cte = next(r for r in results if r.approval_code == "CTE_PCB")
    assert cte.estimated_fee == 100000.0  # Max tier for > 10 Cr
    assert cte.sla_days == 45
    assert cte.stage == RequirementStage.PRE_ESTABLISHMENT

    factory = next(r for r in results if r.approval_code == "FACTORY_LIC")
    assert factory.estimated_fee == 5000.0 + (120 * 100.0)  # 17,000 INR
    assert factory.stage == RequirementStage.POST_COMMISSIONING


def test_white_category_clean_assembly_exemption():
    """Verify that a White-category clean unit below regulatory thresholds requires zero clearances."""
    profile = BusinessProfile(
        business_id="mock-business-id-002",
        manufacturing_activity="Solar panel assembly and LED driver repair",
        industry_scale=IndustryScale.COTTAGE,
        pollution_category=PollutionCategory.WHITE,
        land_area_sqm=200.0,
        total_employees=6,
        plant_machinery_investment=1500000.0,  # 15 Lakhs
        power_requirement_kw=8.0,
        water_requirement_kld=0.5,
    )

    results = evaluate_approval_rules(profile)
    assert len(results) == 0


def test_green_category_concession_and_workforce_trigger():
    """Verify Green category gets 50% fee concession and 15-day SLA, and workforce triggers Factory Act."""
    profile = BusinessProfile(
        business_id="mock-business-id-003",
        manufacturing_activity="Flour mill and organic spice packaging",
        industry_scale=IndustryScale.SMALL_SCALE,
        pollution_category=PollutionCategory.GREEN,
        land_area_sqm=400.0,
        total_employees=18,                   # >= 10 workers with power
        plant_machinery_investment=4000000.0, # 40 Lakhs (< 1 Cr tier base: 10,000)
        power_requirement_kw=30.0,            # <= 50 kW (No HT)
        water_requirement_kld=2.0,            # < 10 KLD (No CGWA)
    )

    results = evaluate_approval_rules(profile)
    codes = {r.approval_code for r in results}

    assert codes == {"CTE_PCB", "CTO_PCB", "FACTORY_LIC"}

    cte = next(r for r in results if r.approval_code == "CTE_PCB")
    assert cte.sla_days == 15                 # Fast track SLA for Green
    assert cte.estimated_fee == 5000.0        # 50% of 10,000

    cto = next(r for r in results if r.approval_code == "CTO_PCB")
    assert cto.sla_days == 15
    assert cto.estimated_fee == 4000.0        # 50% of (10,000 * 0.8)


def test_fire_noc_triggered_by_hazardous_keyword():
    """Verify Fire NOC is triggered even under 500 sqm if activity includes hazardous materials."""
    profile = BusinessProfile(
        business_id="mock-business-id-004",
        manufacturing_activity="Textile dyeing and synthetic solvent formulation",
        industry_scale=IndustryScale.SMALL_SCALE,
        pollution_category=PollutionCategory.ORANGE,
        land_area_sqm=300.0,                  # < 500 sqm
        total_employees=8,
        plant_machinery_investment=3000000.0,
        power_requirement_kw=25.0,
        water_requirement_kld=4.0,
    )

    results = evaluate_approval_rules(profile)
    codes = {r.approval_code for r in results}
    assert "FIRE_NOC" in codes
