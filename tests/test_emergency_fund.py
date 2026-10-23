import pytest
from utils.emergency_fund import EmergencyFundCalculator

def test_recommended_months_calculation():
    # Stable with 0 dependents = 3 months
    assert EmergencyFundCalculator.calculate_recommended_months("stable", 0) == 3
    # Variable income with 2 dependents = 9 + 2 = 11 months
    assert EmergencyFundCalculator.calculate_recommended_months("variable", 2) == 11
    # Moderate with 1 dependent = 6 + 1 = 7 months
    assert EmergencyFundCalculator.calculate_recommended_months("moderate", 1) == 7

def test_evaluate_emergency_fund():
    result = EmergencyFundCalculator.evaluate_emergency_fund(
        monthly_expenses=30000,
        current_savings=150000,
        income_stability="moderate",
        dependents=0,
        monthly_contribution=10000
    )
    assert result["runway_months"] == 5.0
    assert result["tier"] == "Adequate Buffer"
    assert result["status_color"] == "warning"
    assert result["funding_gap"] == 30000.0  # target: 6 * 30000 = 180000 - 150000
    assert result["months_to_goal"] == 3.0   # 30000 / 10000

def test_evaluate_robust_shield():
    result = EmergencyFundCalculator.evaluate_emergency_fund(
        monthly_expenses=20000,
        current_savings=200000,
        income_stability="stable",
        dependents=0
    )
    assert result["runway_months"] == 10.0
    assert result["tier"] == "Robust Shield"
    assert result["status_color"] == "success"
    assert result["funding_gap"] == 0.0

def test_simulate_scenarios():
    scenarios = EmergencyFundCalculator.simulate_scenarios(
        monthly_expenses=25000,
        current_savings=150000
    )
    assert "job_loss" in scenarios
    assert "medical_shock" in scenarios
    assert "austerity_mode" in scenarios
    assert scenarios["job_loss"]["runway_months"] == 6.0
    assert scenarios["austerity_mode"]["extra_months_gained"] > 0
