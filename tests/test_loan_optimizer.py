import pytest
from utils.loan_planner import (
    emi_calculation,
    loan_totals_from_emi,
    financial_check,
    data_input,
    LoanAmortizationOptimizer
)

def test_emi_calculation():
    # 1,00,000 principal at 12% annual interest for 1 year
    res = emi_calculation(principal=100000, rate=12, time=1, income=50000)
    assert round(res["EMI"], 2) == 8884.88
    assert round(res["Net_take_home"], 2) == 41115.12

def test_emi_zero_interest():
    res = emi_calculation(principal=120000, rate=0, time=1, income=30000)
    assert res["EMI"] == 10000.0

def test_financial_check_zones():
    # Zone 1: EMI < 30% of income
    safe = financial_check(emi=2000, income=10000)
    assert safe["Zone"] == 1

    # Zone 0: EMI between 30% and 45%
    moderate = financial_check(emi=3500, income=10000)
    assert moderate["Zone"] == 0

    # Zone -1: EMI >= 45%
    risky = financial_check(emi=5000, income=10000)
    assert risky["Zone"] == -1

    # Invalid income
    with pytest.raises(ValueError):
        financial_check(emi=5000, income=0)

def test_prepayment_impact_reduces_tenure_and_interest():
    optimizer = LoanAmortizationOptimizer()
    # 5,00,000 loan at 10% for 10 years (120 months)
    # Extra monthly prepayment: ₹2,000, Lump sum: ₹50,000 at month 6
    sim = optimizer.calculate_prepayment_impact(
        principal=500000,
        annual_rate=10,
        tenure_years=10,
        extra_monthly=2000,
        lump_sum=50000,
        lump_sum_month=6
    )

    baseline = sim["baseline"]
    accel = sim["accelerated"]

    assert baseline["total_months"] == 120
    assert accel["total_months"] < 120
    assert accel["months_saved"] > 0
    assert accel["interest_saved"] > 0
    assert accel["total_payment"] < baseline["total_payment"]
    assert len(sim["schedule_preview"]) > 0

def test_compare_payoff_strategies_avalanche_vs_snowball():
    optimizer = LoanAmortizationOptimizer()
    debts = [
        {"name": "Credit Card", "balance": 50000, "interest_rate": 36.0, "min_payment": 2000},
        {"name": "Personal Loan", "balance": 150000, "interest_rate": 15.0, "min_payment": 4500},
        {"name": "Auto Loan", "balance": 300000, "interest_rate": 9.0, "min_payment": 7000}
    ]

    result = optimizer.compare_payoff_strategies(debts, extra_monthly_budget=5000)
    assert "avalanche" in result
    assert "snowball" in result

    # Avalanche (highest rate first) should pay less or equal total interest than Snowball
    assert result["avalanche"]["total_interest_paid"] <= result["snowball"]["total_interest_paid"]
    assert result["interest_difference"] >= 0
    assert "recommendation" in result
