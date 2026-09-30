"""
Statutory Regulatory Rules Engine (Fragment 44).
Encodes statutory acts, government circulars, and environmental thresholds to deterministically
evaluate which clearances, permits, and NOCs are mandatory for an enterprise unit.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional
from app.models.approval_requirement import RequirementStage
from app.models.business_profile import BusinessProfile, PollutionCategory


@dataclass(frozen=True)
class RuleEvaluationResult:
    """Outcome of statutory clearance rule evaluation."""
    approval_code: str
    approval_title: str
    department_code: str
    issuing_authority: str
    statutory_act: str
    stage: RequirementStage
    priority: int
    is_mandatory: bool
    sla_days: int
    estimated_fee: float
    trigger_reason: str


@dataclass(frozen=True)
class StatutoryRule:
    """Definition of a statutory approval rule and its triggering predicate."""
    code: str
    title: str
    department_code: str
    issuing_authority: str
    statutory_act: str
    stage: RequirementStage
    priority: int
    is_mandatory: bool
    base_sla_days: int
    evaluator: Callable[[BusinessProfile], Optional[RuleEvaluationResult]]


def _calc_pcb_fee(investment: Optional[float]) -> float:
    """Calculate SPCB statutory fee scaled by plant & machinery capital investment."""
    inv = investment or 0.0
    if inv < 10000000.0:  # < 1 Cr
        return 10000.0
    elif inv < 50000000.0:  # 1 Cr - 5 Cr
        return 25000.0
    elif inv < 100000000.0:  # 5 Cr - 10 Cr
        return 50000.0
    else:  # >= 10 Cr
        return 100000.0


def _evaluate_cte_pcb(profile: BusinessProfile) -> Optional[RuleEvaluationResult]:
    """Evaluate Consent to Establish (CTE) under Water & Air Acts."""
    category = profile.pollution_category
    if category in (PollutionCategory.RED, PollutionCategory.ORANGE, PollutionCategory.GREEN):
        is_green = (category == PollutionCategory.GREEN)
        sla = 15 if is_green else 45
        fee = _calc_pcb_fee(profile.plant_machinery_investment)
        if is_green:
            fee *= 0.5  # 50% concession for green category units

        reason = (
            f"Mandatory under Water Act 1974 & Air Act 1981: CPCB classified unit as "
            f"'{category.value}' category requiring prior environmental clearance before civil construction."
        )
        return RuleEvaluationResult(
            approval_code="CTE_PCB",
            approval_title="Consent to Establish (CTE) under Water & Air Acts",
            department_code="SPCB",
            issuing_authority="State Pollution Control Board",
            statutory_act="Water Act 1974 & Air Act 1981",
            stage=RequirementStage.PRE_ESTABLISHMENT,
            priority=1,
            is_mandatory=True,
            sla_days=sla,
            estimated_fee=fee,
            trigger_reason=reason,
        )
    return None


def _evaluate_cto_pcb(profile: BusinessProfile) -> Optional[RuleEvaluationResult]:
    """Evaluate Consent to Operate (CTO) under Water & Air Acts."""
    category = profile.pollution_category
    if category in (PollutionCategory.RED, PollutionCategory.ORANGE, PollutionCategory.GREEN):
        is_green = (category == PollutionCategory.GREEN)
        sla = 15 if is_green else 30
        fee = _calc_pcb_fee(profile.plant_machinery_investment) * 0.8
        if is_green:
            fee *= 0.5

        reason = (
            f"Mandatory prior to trial production / commercial commissioning to verify installation "
            f"and compliance of Effluent Treatment Plant (ETP) / Air Pollution Control Devices."
        )
        return RuleEvaluationResult(
            approval_code="CTO_PCB",
            approval_title="Consent to Operate (CTO) under Water & Air Acts",
            department_code="SPCB",
            issuing_authority="State Pollution Control Board",
            statutory_act="Water Act 1974 & Air Act 1981",
            stage=RequirementStage.PRE_COMMISSIONING,
            priority=2,
            is_mandatory=True,
            sla_days=sla,
            estimated_fee=fee,
            trigger_reason=reason,
        )
    return None


def _evaluate_factory_lic(profile: BusinessProfile) -> Optional[RuleEvaluationResult]:
    """Evaluate Factory License under Factories Act 1948."""
    workers = profile.total_employees or 0
    power = profile.power_requirement_kw or 0.0

    # Section 2(m): 10 or more workers with power, or 20 or more without power
    triggered = (workers >= 10 and power > 0) or (workers >= 20)
    if triggered:
        fee = 5000.0 + (workers * 100.0)
        reason = (
            f"Factories Act 1948 (Sec 6 & 7): Unit employs {workers} workers with "
            f"{power:.1f} kW power machinery, qualifying as a registered factory."
        )
        return RuleEvaluationResult(
            approval_code="FACTORY_LIC",
            approval_title="Factory License & Factory Plan Approval",
            department_code="DISH",
            issuing_authority="Directorate of Industrial Safety and Health (DISH)",
            statutory_act="Factories Act, 1948",
            stage=RequirementStage.POST_COMMISSIONING,
            priority=2,
            is_mandatory=True,
            sla_days=30,
            estimated_fee=fee,
            trigger_reason=reason,
        )
    return None


def _evaluate_fire_noc(profile: BusinessProfile) -> Optional[RuleEvaluationResult]:
    """Evaluate Fire Safety Clearance / NOC."""
    land_area = profile.land_area_sqm or 0.0
    activity = (profile.manufacturing_activity or "").lower()
    is_hazardous = profile.pollution_category == PollutionCategory.RED or any(
        hz in activity for hz in ["chemical", "paint", "solvent", "petroleum", "explosive", "textile", "rubber"]
    )

    if land_area >= 500.0 or is_hazardous:
        fee = 15000.0
        reason = (
            f"State Fire Prevention & Life Safety Act: Plot area ({land_area:.0f} sqm >= 500 sqm) "
            f"or flammable/hazardous manufacturing profile mandates prior fire safety approval."
        )
        return RuleEvaluationResult(
            approval_code="FIRE_NOC",
            approval_title="Provisional Fire Safety Approval & Fire NOC",
            department_code="FIRE",
            issuing_authority="State Fire and Emergency Services",
            statutory_act="State Fire Prevention and Life Safety Measures Act",
            stage=RequirementStage.PRE_ESTABLISHMENT,
            priority=1,
            is_mandatory=True,
            sla_days=21,
            estimated_fee=fee,
            trigger_reason=reason,
        )
    return None


def _evaluate_power_ht(profile: BusinessProfile) -> Optional[RuleEvaluationResult]:
    """Evaluate High Tension Power Connection & CEI Approval."""
    power = profile.power_requirement_kw or 0.0
    if power > 50.0:
        fee = 25000.0
        reason = (
            f"Electricity Act 2003: Connected load of {power:.1f} kW exceeds the 50 kW Low Tension limit, "
            f"mandating High Tension (HT) 11kV/33kV supply infrastructure and Chief Electrical Inspectorate inspection."
        )
        return RuleEvaluationResult(
            approval_code="POWER_HT",
            approval_title="High Tension (HT) Industrial Power Sanction & CEI Inspection",
            department_code="DISCOM",
            issuing_authority="Power Distribution Company & Chief Electrical Inspectorate",
            statutory_act="Electricity Act, 2003",
            stage=RequirementStage.PRE_COMMISSIONING,
            priority=2,
            is_mandatory=True,
            sla_days=30,
            estimated_fee=fee,
            trigger_reason=reason,
        )
    return None


def _evaluate_cgwa_gw(profile: BusinessProfile) -> Optional[RuleEvaluationResult]:
    """Evaluate Central Ground Water Authority (CGWA) Extraction NOC."""
    water = profile.water_requirement_kld or 0.0
    if water >= 10.0:
        fee = 20000.0
        reason = (
            f"Environment (Protection) Act 1986 / CGWA Guidelines: Daily industrial water abstraction of "
            f"{water:.1f} KLD exceeds the 10 KLD regulatory threshold, requiring statutory ground water NOC."
        )
        return RuleEvaluationResult(
            approval_code="CGWA_GW",
            approval_title="Ground Water Abstraction & Tube-well NOC",
            department_code="CGWA",
            issuing_authority="Central Ground Water Authority",
            statutory_act="Environment (Protection) Act, 1986",
            stage=RequirementStage.PRE_ESTABLISHMENT,
            priority=2,
            is_mandatory=True,
            sla_days=45,
            estimated_fee=fee,
            trigger_reason=reason,
        )
    return None


STATUTORY_RULES: List[StatutoryRule] = [
    StatutoryRule(
        code="CTE_PCB",
        title="Consent to Establish (CTE) under Water & Air Acts",
        department_code="SPCB",
        issuing_authority="State Pollution Control Board",
        statutory_act="Water Act 1974 & Air Act 1981",
        stage=RequirementStage.PRE_ESTABLISHMENT,
        priority=1,
        is_mandatory=True,
        base_sla_days=45,
        evaluator=_evaluate_cte_pcb,
    ),
    StatutoryRule(
        code="CTO_PCB",
        title="Consent to Operate (CTO) under Water & Air Acts",
        department_code="SPCB",
        issuing_authority="State Pollution Control Board",
        statutory_act="Water Act 1974 & Air Act 1981",
        stage=RequirementStage.PRE_COMMISSIONING,
        priority=2,
        is_mandatory=True,
        base_sla_days=30,
        evaluator=_evaluate_cto_pcb,
    ),
    StatutoryRule(
        code="FIRE_NOC",
        title="Provisional Fire Safety Approval & Fire NOC",
        department_code="FIRE",
        issuing_authority="State Fire and Emergency Services",
        statutory_act="State Fire Prevention and Life Safety Measures Act",
        stage=RequirementStage.PRE_ESTABLISHMENT,
        priority=1,
        is_mandatory=True,
        base_sla_days=21,
        evaluator=_evaluate_fire_noc,
    ),
    StatutoryRule(
        code="POWER_HT",
        title="High Tension (HT) Industrial Power Sanction & CEI Inspection",
        department_code="DISCOM",
        issuing_authority="Power Distribution Company & Chief Electrical Inspectorate",
        statutory_act="Electricity Act, 2003",
        stage=RequirementStage.PRE_COMMISSIONING,
        priority=2,
        is_mandatory=True,
        base_sla_days=30,
        evaluator=_evaluate_power_ht,
    ),
    StatutoryRule(
        code="FACTORY_LIC",
        title="Factory License & Factory Plan Approval",
        department_code="DISH",
        issuing_authority="Directorate of Industrial Safety and Health (DISH)",
        statutory_act="Factories Act, 1948",
        stage=RequirementStage.POST_COMMISSIONING,
        priority=2,
        is_mandatory=True,
        base_sla_days=30,
        evaluator=_evaluate_factory_lic,
    ),
    StatutoryRule(
        code="CGWA_GW",
        title="Ground Water Abstraction & Tube-well NOC",
        department_code="CGWA",
        issuing_authority="Central Ground Water Authority",
        statutory_act="Environment (Protection) Act, 1986",
        stage=RequirementStage.PRE_ESTABLISHMENT,
        priority=2,
        is_mandatory=True,
        base_sla_days=45,
        evaluator=_evaluate_cgwa_gw,
    ),
]


def evaluate_approval_rules(profile: BusinessProfile) -> List[RuleEvaluationResult]:
    """
    Deterministically evaluate all statutory clearance rules against an industrial profile.
    Returns matched clearances with statutory rationales and calculated fees.
    """
    matched: List[RuleEvaluationResult] = []
    for rule in STATUTORY_RULES:
        result = rule.evaluator(profile)
        if result is not None:
            matched.append(result)
    return matched
