"""
Loan Amortization & Debt Payoff Strategy Optimizer.
Calculates EMI, amortization schedules, prepayment savings, tenure reductions,
and evaluates Debt Avalanche vs. Debt Snowball payoff strategies.
"""

from typing import Dict, Any, List, Optional
import os
import json
from dotenv import load_dotenv

load_dotenv()

_groq_client = None


def get_groq_client():
    """Lazily load Groq client to prevent import crashes when API key is missing."""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key and api_key != "YOUR_API_KEY":
            try:
                from groq import Groq
                _groq_client = Groq(api_key=api_key)
            except Exception:
                _groq_client = None
    return _groq_client


def loan_totals_from_emi(principal: float, emi: float, time: float) -> Dict[str, float]:
    """Derives amortization-consistent totals from EMI and tenure in years."""
    total_paid = emi * time * 12
    total_interest = max(0.0, total_paid - principal)
    return {"Amount": total_paid, "Interest": total_interest}


def emi_calculation(principal: float, rate: float, time: float, income: float) -> Dict[str, float]:
    """Calculate monthly EMI and net take-home income."""
    principal = float(principal)
    rate = float(rate)
    time = float(time)
    income = float(income)
    
    m_rate = (rate / 12) / 100
    m_time = int(time * 12)
    try:
        if m_rate == 0:
            emi = principal / m_time if m_time > 0 else 0.0
        else:
            emi = (principal * m_rate * ((1 + m_rate) ** m_time)) / (((1 + m_rate) ** m_time) - 1)
    except Exception:
        emi = 0.0
    net = max(0.0, income - emi)
    return {"EMI": emi, "Net_take_home": net}


def financial_check(emi: float, income: float) -> Dict[str, float]:
    """Check EMI to income ratio and assign financial risk zone."""
    if income is None or income <= 0:
        raise ValueError("Income must be greater than 0")
    ratio = emi / income
    percentage = ratio * 100
    if percentage < 30:
        zone = 1  # Safe
    elif percentage < 45:
        zone = 0  # Moderate
    else:
        zone = -1  # Risky
    return {"Ratio": ratio, "Zone": zone}


def financial_advice(message: Any) -> str:
    """Generate LLM-based financial advice with safe fallback."""
    client = get_groq_client()
    if not client:
        return "AI advisory service is currently in offline mode. Ensure your EMI does not exceed 35% of monthly net income."
    try:
        user_prompt_string = json.dumps(message, indent=2)
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a loan advisor. Based on the info provided, provide the answers to the following questions: "
                        "Are there any risks associated with the loan? What should they improve to make the loan suitable for them? "
                        "All prices are in rupees. For zone, 1 is safe, 0 is moderate, -1 is risky. Be concise, actionable, and accurate."
                    )
                },
                {"role": "user", "content": f"Here are the financial metrics:{user_prompt_string}"}
            ]
        )
        return res.choices[0].message.content
    except Exception as e:
        print("Groq advisory warning:", e)
        return "AI advisory service is temporarily unavailable. Consider maintaining a safe debt-to-income ratio below 35%."


def data_input(principal: float, rate: float, time: float, income: float) -> Dict[str, Any]:
    """Process loan input and calculate key metrics (backward-compatible entry point)."""
    emi_calc = emi_calculation(principal, rate, time, income)
    emi = emi_calc.get("EMI", 0)
    loan_calc = loan_totals_from_emi(principal, emi, time)
    check = financial_check(emi, income)
    metrics = {
        "Loan_Amount": loan_calc.get("Amount", 0),
        "Loan_Interest": loan_calc.get("Interest", 0),
        "EMI": emi,
        "Net_take_income": emi_calc.get("Net_take_home", 0),
        "EMI to Income Ratio": check.get("Ratio", 0),
        "Zone": check.get("Zone", 0)
    }
    advice = financial_advice(metrics)
    return {
        "Loan_Amount": round(loan_calc.get("Amount", 0), 2),
        "Loan_Interest": round(loan_calc.get("Interest", 0), 2),
        "EMI": round(emi, 2),
        "Net_take_income": round(emi_calc.get("Net_take_home", 0), 2),
        "Ratio": round(check.get("Ratio", 0), 2),
        "Zone": round(check.get("Zone", 0), 2),
        "Advice": advice
    }


class LoanAmortizationOptimizer:
    """Advanced loan prepayment simulation and multi-debt strategy engine."""

    @staticmethod
    def calculate_prepayment_impact(
        principal: float,
        annual_rate: float,
        tenure_years: float,
        extra_monthly: float = 0.0,
        lump_sum: float = 0.0,
        lump_sum_month: int = 1
    ) -> Dict[str, Any]:
        """
        Simulate the effect of extra monthly payments and one-time lump-sum prepayment.
        Returns original schedule totals vs accelerated payoff totals and savings.
        """
        principal = max(0.0, float(principal))
        annual_rate = max(0.0, float(annual_rate))
        tenure_years = max(0.1, float(tenure_years))
        extra_monthly = max(0.0, float(extra_monthly))
        lump_sum = max(0.0, float(lump_sum))
        lump_sum_month = max(1, int(lump_sum_month))

        monthly_rate = (annual_rate / 12) / 100
        original_months = int(tenure_years * 12)

        # Baseline EMI
        if monthly_rate == 0:
            baseline_emi = principal / original_months if original_months > 0 else 0.0
        else:
            baseline_emi = (
                principal * monthly_rate * ((1 + monthly_rate) ** original_months)
            ) / (((1 + monthly_rate) ** original_months) - 1)

        original_total_interest = max(0.0, (baseline_emi * original_months) - principal)
        original_total_payment = principal + original_total_interest

        # Accelerated simulation
        balance = principal
        accelerated_total_interest = 0.0
        accelerated_months = 0
        schedule_preview = []

        while balance > 0.01 and accelerated_months < original_months * 2:
            accelerated_months += 1
            interest_month = balance * monthly_rate
            accelerated_total_interest += interest_month

            regular_principal_component = min(balance, baseline_emi - interest_month)
            balance -= regular_principal_component

            # Apply extra monthly prepayment
            if extra_monthly > 0 and balance > 0:
                extra_paid = min(balance, extra_monthly)
                balance -= extra_paid

            # Apply lump-sum prepayment at specified month
            if accelerated_months == lump_sum_month and lump_sum > 0 and balance > 0:
                lump_paid = min(balance, lump_sum)
                balance -= lump_paid

            # Keep first 12 months for chart/schedule preview
            if accelerated_months <= 12 or balance <= 0.01:
                schedule_preview.append({
                    "month": accelerated_months,
                    "remaining_balance": round(max(0.0, balance), 2),
                    "interest_paid": round(interest_month, 2)
                })

        months_saved = max(0, original_months - accelerated_months)
        interest_saved = max(0.0, original_total_interest - accelerated_total_interest)
        accelerated_total_payment = principal + accelerated_total_interest

        years_saved = round(months_saved / 12, 1)

        return {
            "baseline": {
                "emi": round(baseline_emi, 2),
                "total_months": original_months,
                "total_interest": round(original_total_interest, 2),
                "total_payment": round(original_total_payment, 2)
            },
            "accelerated": {
                "effective_monthly_payment": round(baseline_emi + extra_monthly, 2),
                "total_months": accelerated_months,
                "total_interest": round(accelerated_total_interest, 2),
                "total_payment": round(accelerated_total_payment, 2),
                "months_saved": months_saved,
                "years_saved": years_saved,
                "interest_saved": round(interest_saved, 2),
                "interest_reduction_percent": round(
                    (interest_saved / original_total_interest * 100), 1
                ) if original_total_interest > 0 else 0.0
            },
            "schedule_preview": schedule_preview
        }

    @staticmethod
    def compare_payoff_strategies(
        debts: List[Dict[str, Any]],
        extra_monthly_budget: float = 0.0
    ) -> Dict[str, Any]:
        """
        Compare Debt Avalanche (Highest Interest Rate First) vs
        Debt Snowball (Lowest Balance First).
        Each debt dict should have: name, balance, interest_rate, min_payment.
        """
        extra_budget = max(0.0, float(extra_monthly_budget))

        if not debts:
            return {"error": "No debts provided"}

        def simulate_strategy(sort_key, reverse=True):
            ordered_debts = sorted(
                [dict(d) for d in debts],
                key=sort_key,
                reverse=reverse
            )
            # Validate numeric values
            for d in ordered_debts:
                d["balance"] = float(d.get("balance", 0))
                d["rate"] = float(d.get("interest_rate", 0))
                d["min_payment"] = float(d.get("min_payment", 0))
                d["cleared_month"] = None

            month = 0
            total_interest = 0.0
            clearance_timeline = []

            while any(d["balance"] > 0.01 for d in ordered_debts) and month < 360:
                month += 1
                freed_up_payments = 0.0

                # Accrue interest and pay minimums
                for d in ordered_debts:
                    if d["balance"] > 0:
                        m_rate = (d["rate"] / 12) / 100
                        interest = d["balance"] * m_rate
                        total_interest += interest
                        d["balance"] += interest

                        # Pay minimum payment
                        payment = min(d["balance"], d["min_payment"])
                        d["balance"] -= payment
                        if d["balance"] <= 0.01:
                            d["balance"] = 0.0
                            if d["cleared_month"] is None:
                                d["cleared_month"] = month
                                clearance_timeline.append({
                                    "debt": d["name"],
                                    "cleared_at_month": month
                                })
                    else:
                        freed_up_payments += d["min_payment"]

                # Apply extra budget + freed up minimum payments to priority target
                available_extra = extra_budget + freed_up_payments
                for d in ordered_debts:
                    if d["balance"] > 0 and available_extra > 0:
                        extra_paid = min(d["balance"], available_extra)
                        d["balance"] -= extra_paid
                        available_extra -= extra_paid
                        if d["balance"] <= 0.01:
                            d["balance"] = 0.0
                            if d["cleared_month"] is None:
                                d["cleared_month"] = month
                                clearance_timeline.append({
                                    "debt": d["name"],
                                    "cleared_at_month": month
                                })

            return {
                "total_months": month,
                "total_interest_paid": round(total_interest, 2),
                "clearance_order": clearance_timeline
            }

        # Avalanche: Highest rate first (descending rate)
        avalanche_result = simulate_strategy(lambda x: x.get("interest_rate", 0), reverse=True)
        # Snowball: Lowest balance first (ascending balance)
        snowball_result = simulate_strategy(lambda x: x.get("balance", 0), reverse=False)

        interest_diff = round(snowball_result["total_interest_paid"] - avalanche_result["total_interest_paid"], 2)

        return {
            "avalanche": avalanche_result,
            "snowball": snowball_result,
            "interest_difference": interest_diff,
            "recommendation": (
                "Debt Avalanche minimizes total interest paid and saves you ₹{:,.2f}.".format(interest_diff)
                if interest_diff > 0
                else "Both strategies offer similar financial efficiency. Choose Snowball for psychological momentum."
            )
        }
