"""
MSME Investment, Plant & Machinery Capital Tracking, and Incentive Calculation Engine.
Implements the MSMED Act 2020 composite criteria for Micro, Small, and Medium classifications,
as well as capital investment subsidy tier evaluations.
"""

from dataclasses import dataclass
from typing import List, Optional
from app.models.business import MSMECategory


@dataclass
class InvestmentEvaluation:
    computed_category: MSMECategory
    investment_amount: float
    annual_turnover: float
    cgtmse_credit_cover_max_cr: float
    estimated_capital_subsidy_pct: float
    estimated_capital_subsidy_inr: float
    interest_subvention_pct: float
    is_eligible_for_msme_schemes: bool
    statutory_notes: List[str]


# Statutory MSMED Act 2020 Composite Criteria (Values in INR)
# Both investment and turnover criteria must be satisfied for a lower tier;
# exceeding either pushes enterprise into the next tier.
MICRO_MAX_INVESTMENT = 10_000_000.0       # ₹1 Crore
MICRO_MAX_TURNOVER = 50_000_000.0         # ₹5 Crore

SMALL_MAX_INVESTMENT = 100_000_000.0      # ₹10 Crore
SMALL_MAX_TURNOVER = 500_000_000.0        # ₹50 Crore

MEDIUM_MAX_INVESTMENT = 500_000_000.0     # ₹50 Crore
MEDIUM_MAX_TURNOVER = 2_500_000_000.0     # ₹250 Crore


def calculate_msme_category(
    plant_machinery_investment: float,
    annual_turnover: float,
) -> MSMECategory:
    """
    Compute MSME classification based on MSMED Act 2020 composite criteria.
    Both investment and turnover limits must be met.
    """
    inv = max(0.0, plant_machinery_investment)
    to = max(0.0, annual_turnover)

    if inv <= MICRO_MAX_INVESTMENT and to <= MICRO_MAX_TURNOVER:
        return MSMECategory.MICRO
    elif inv <= SMALL_MAX_INVESTMENT and to <= SMALL_MAX_TURNOVER:
        return MSMECategory.SMALL
    elif inv <= MEDIUM_MAX_INVESTMENT and to <= MEDIUM_MAX_TURNOVER:
        return MSMECategory.MEDIUM
    else:
        return MSMECategory.LARGE


def evaluate_investment_profile(
    plant_machinery_investment: float,
    annual_turnover: float,
    state: Optional[str] = None,
    is_backward_district: bool = False,
) -> InvestmentEvaluation:
    """
    Evaluate enterprise capital investment profile, statutory category,
    CGTMSE credit guarantee limits, and estimated state/central industrial incentives.
    """
    category = calculate_msme_category(plant_machinery_investment, annual_turnover)
    notes: List[str] = []

    # 1. CGTMSE Credit Guarantee Collateral-free Loan Ceiling
    if category == MSMECategory.MICRO:
        cgtmse_max = 5.0  # ₹5 Crore max guarantee
        notes.append("Eligible for 85% credit guarantee coverage up to ₹5 Crore under CGTMSE.")
    elif category == MSMECategory.SMALL:
        cgtmse_max = 5.0
        notes.append("Eligible for 75% credit guarantee coverage up to ₹5 Crore under CGTMSE.")
    elif category == MSMECategory.MEDIUM:
        cgtmse_max = 5.0
        notes.append("Eligible for standard MSME institutional credit facilities.")
    else:
        cgtmse_max = 0.0
        notes.append("Non-MSME Large enterprise: Standard corporate banking facilities apply.")

    # 2. Capital Subsidy Estimation (State + Central MSME policies)
    # Higher subsidy for Micro/Small and in notified backward/developing industrial districts
    if category == MSMECategory.MICRO:
        base_subsidy = 25.0 if is_backward_district else 15.0
        interest_sub = 5.0
    elif category == MSMECategory.SMALL:
        base_subsidy = 20.0 if is_backward_district else 10.0
        interest_sub = 4.0
    elif category == MSMECategory.MEDIUM:
        base_subsidy = 15.0 if is_backward_district else 7.5
        interest_sub = 2.5
    else:
        base_subsidy = 5.0 if is_backward_district else 0.0
        interest_sub = 0.0

    subsidy_amount = (plant_machinery_investment * base_subsidy) / 100.0

    if base_subsidy > 0:
        notes.append(
            f"Estimated capital investment subsidy of {base_subsidy}% (approx ₹{subsidy_amount:,.2f}) available under state industrial promotion policies."
        )
    if interest_sub > 0:
        notes.append(f"Eligible for {interest_sub}% annual interest subvention on term loans.")

    return InvestmentEvaluation(
        computed_category=category,
        investment_amount=plant_machinery_investment,
        annual_turnover=annual_turnover,
        cgtmse_credit_cover_max_cr=cgtmse_max,
        estimated_capital_subsidy_pct=base_subsidy,
        estimated_capital_subsidy_inr=subsidy_amount,
        interest_subvention_pct=interest_sub,
        is_eligible_for_msme_schemes=(category != MSMECategory.LARGE),
        statutory_notes=notes,
    )
