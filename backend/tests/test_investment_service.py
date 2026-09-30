"""
Tests for MSME Investment, Plant & Machinery Capital Tracking, and Incentive Evaluation.
"""

import pytest
from app.models.business import MSMECategory
from app.services.investment_service import (
    calculate_msme_category,
    evaluate_investment_profile,
)


def test_msme_composite_micro_classification():
    """Verify Micro enterprise limits (Inv <= 1 Cr, Turnover <= 5 Cr)."""
    # 50 Lakh investment, 2 Crore turnover -> MICRO
    cat = calculate_msme_category(5_000_000.0, 20_000_000.0)
    assert cat == MSMECategory.MICRO

    # Boundary exactly 1 Cr and 5 Cr
    cat_boundary = calculate_msme_category(10_000_000.0, 50_000_000.0)
    assert cat_boundary == MSMECategory.MICRO


def test_msme_composite_exceeding_threshold_pushes_tier():
    """Verify exceeding either investment or turnover pushes enterprise to next tier."""
    # Low investment (80 Lakhs, Micro level), but high turnover (15 Crore, Small level) -> SMALL
    cat = calculate_msme_category(8_000_000.0, 150_000_000.0)
    assert cat == MSMECategory.SMALL

    # High investment (2 Crore, Small level), but low turnover (3 Crore, Micro level) -> SMALL
    cat2 = calculate_msme_category(20_000_000.0, 30_000_000.0)
    assert cat2 == MSMECategory.SMALL


def test_msme_composite_medium_and_large():
    """Verify Medium (Inv <= 50 Cr, Turnover <= 250 Cr) and Large categories."""
    # 35 Crore investment, 120 Crore turnover -> MEDIUM
    cat_med = calculate_msme_category(350_000_000.0, 1_200_000_000.0)
    assert cat_med == MSMECategory.MEDIUM

    # 60 Crore investment -> LARGE
    cat_large = calculate_msme_category(600_000_000.0, 500_000_000.0)
    assert cat_large == MSMECategory.LARGE

    # 20 Crore investment, but 300 Crore turnover -> LARGE
    cat_large_to = calculate_msme_category(200_000_000.0, 3_000_000_000.0)
    assert cat_large_to == MSMECategory.LARGE


def test_investment_incentive_evaluation():
    """Verify capital subsidy percentage and CGTMSE cover computation."""
    # Small enterprise in developing industrial district
    eval_res = evaluate_investment_profile(
        plant_machinery_investment=40_000_000.0,
        annual_turnover=150_000_000.0,
        state="Maharashtra",
        is_backward_district=True,
    )

    assert eval_res.computed_category == MSMECategory.SMALL
    assert eval_res.cgtmse_credit_cover_max_cr == 5.0
    assert eval_res.estimated_capital_subsidy_pct == 20.0  # 20% in backward district
    assert eval_res.estimated_capital_subsidy_inr == 8_000_000.0  # 20% of 4 Cr = 80 Lakh
    assert eval_res.interest_subvention_pct == 4.0
    assert eval_res.is_eligible_for_msme_schemes is True
    assert len(eval_res.statutory_notes) >= 2


def test_large_enterprise_incentive_evaluation():
    """Verify Large enterprise incentive exclusions."""
    eval_large = evaluate_investment_profile(
        plant_machinery_investment=700_000_000.0,
        annual_turnover=4_000_000_000.0,
        state="Gujarat",
        is_backward_district=False,
    )

    assert eval_large.computed_category == MSMECategory.LARGE
    assert eval_large.is_eligible_for_msme_schemes is False
    assert eval_large.cgtmse_credit_cover_max_cr == 0.0
