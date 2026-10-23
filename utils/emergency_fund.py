"""
Emergency Fund & Financial Runway Simulator Engine.
Provides runway calculation, tiered safety net recommendations,
and stress-test scenario simulations for personal financial security.
"""

from typing import Dict, Any, Optional
from datetime import datetime


class EmergencyFundCalculator:
    """Calculates emergency fund needs and simulates survival runway."""

    @staticmethod
    def calculate_recommended_months(income_stability: str = "moderate", dependents: int = 0) -> int:
        """Calculate recommended emergency buffer in months based on risk profile."""
        stability = income_stability.lower().strip()
        
        if stability == "stable":
            base = 3
        elif stability == "variable":
            base = 9
        else:  # moderate / single-income salaried
            base = 6
            
        additional = max(0, min(dependents, 6))  # 1 month per dependent, max +6
        total = base + additional
        return min(total, 18)

    @classmethod
    def evaluate_emergency_fund(
        cls,
        monthly_expenses: float,
        current_savings: float,
        income_stability: str = "moderate",
        dependents: int = 0,
        monthly_contribution: float = 0.0,
        custom_target_months: Optional[int] = None
    ) -> Dict[str, Any]:
        """Comprehensive evaluation of current emergency reserves."""
        monthly_burn = max(0.0, float(monthly_expenses))
        savings = max(0.0, float(current_savings))
        contribution = max(0.0, float(monthly_contribution))
        
        target_months = custom_target_months if custom_target_months and custom_target_months > 0 else cls.calculate_recommended_months(income_stability, dependents)
        target_amount = target_months * monthly_burn
        
        runway_months = round(savings / monthly_burn, 1) if monthly_burn > 0 else 0.0
        funding_gap = max(0.0, target_amount - savings)
        funded_pct = round((savings / target_amount * 100), 1) if target_amount > 0 else 100.0
        funded_pct = min(100.0, funded_pct)
        
        months_to_goal = None
        if funding_gap > 0 and contribution > 0:
            months_to_goal = round(funding_gap / contribution, 1)
            
        if runway_months >= 6.0:
            tier = "Robust Shield"
            status_color = "success"
            message = "Your financial safety net provides outstanding resilience against unexpected income disruptions."
        elif runway_months >= 3.0:
            tier = "Adequate Buffer"
            status_color = "warning"
            message = "You have a baseline emergency buffer, but additional reserves are recommended for family protection."
        else:
            tier = "Vulnerable Runway"
            status_color = "danger"
            message = "High risk: Your emergency reserve covers less than 3 months of essential living expenses."
            
        return {
            "monthly_expenses": monthly_burn,
            "current_savings": savings,
            "target_months": target_months,
            "target_amount": round(target_amount, 2),
            "runway_months": runway_months,
            "funding_gap": round(funding_gap, 2),
            "funded_percentage": funded_pct,
            "monthly_contribution": contribution,
            "months_to_goal": months_to_goal,
            "tier": tier,
            "status_color": status_color,
            "summary_message": message
        }

    @staticmethod
    def simulate_scenarios(monthly_expenses: float, current_savings: float) -> Dict[str, Any]:
        """Simulate common financial emergencies and runway impacts."""
        monthly_burn = max(1.0, float(monthly_expenses))
        savings = max(0.0, float(current_savings))
        
        # 1. Total Job Loss (Zero income, full burn)
        job_loss_months = round(savings / monthly_burn, 1)
        job_loss_days = int(job_loss_months * 30)
        
        # 2. Medical Expense Shock (Immediate out-of-pocket hit of ₹1,00,000 or 2 months burn)
        shock_amount = min(savings, max(100000.0, monthly_burn * 2))
        remaining_after_shock = max(0.0, savings - shock_amount)
        runway_after_shock = round(remaining_after_shock / monthly_burn, 1)
        
        # 3. Austerity Mode (Cutting discretionary spend by 30%)
        lean_burn = monthly_burn * 0.70
        lean_runway_months = round(savings / lean_burn, 1) if lean_burn > 0 else 0.0
        runway_extension_months = round(lean_runway_months - job_loss_months, 1)
        
        return {
            "job_loss": {
                "runway_months": job_loss_months,
                "runway_days": job_loss_days,
                "description": f"With zero income, your savings will sustain current living costs for {job_loss_months} months."
            },
            "medical_shock": {
                "shock_amount": round(shock_amount, 2),
                "remaining_savings": round(remaining_after_shock, 2),
                "runway_after_shock_months": runway_after_shock,
                "description": f"After absorbing a ₹{shock_amount:,.0f} emergency shock, you retain {runway_after_shock} months of runway."
            },
            "austerity_mode": {
                "lean_monthly_burn": round(lean_burn, 2),
                "extended_runway_months": lean_runway_months,
                "extra_months_gained": runway_extension_months,
                "description": f"Trimming non-essentials by 30% extends your runway by an additional {runway_extension_months} months."
            }
        }
