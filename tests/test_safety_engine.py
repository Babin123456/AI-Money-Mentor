"""
Unit tests for SafetyEngine compliance and guardrails verification.
"""

import pytest
from utils.safety_engine import SafetyEngine


def test_safety_engine_clean_response():
    engine = SafetyEngine()
    response = (
        "Based on your profile, investing in diversified index funds can help grow your wealth over time. "
        "Historically, equity markets have yielded attractive returns, though past performance is not indicative of future results. "
        "Please consult a financial advisor before making significant asset allocation decisions."
    )
    context = {"income": 1000000, "savings": 200000}
    result = engine.process_response(response, context)

    assert result["passed"] is True
    assert len(result["violations"]) == 0
    assert result["confidence_score"] >= 70


def test_safety_engine_prohibited_terms():
    engine = SafetyEngine()
    response = (
        "This crypto scheme provides guaranteed returns with 100% safe profits and double your money in 6 months! "
        "Consult a financial advisor."
    )
    result = engine.process_response(response, {})

    assert result["passed"] is False
    assert any("Prohibited term" in v for v in result["violations"])


def test_safety_engine_privacy_violation():
    engine = SafetyEngine()
    response = (
        "Your account details are linked with PAN ABCDE1234F. "
        "Consult a financial advisor for your tax filings."
    )
    result = engine.process_response(response, {})

    assert result["passed"] is False
    assert any("Privacy violation" in v or "PAN exposed" in v for v in result["violations"])


def test_safety_engine_generate_safe_response():
    engine = SafetyEngine()
    violations = ["Prohibited term detected: guaranteed returns", "Privacy violation: PAN exposed"]
    warnings = ["Missing financial advisory disclaimer"]

    safe_response = engine.generate_safe_response(violations, warnings)

    assert "⚠️ **Safety Check: AI Response Modified**" in safe_response
    assert "Issues detected:" in safe_response
    assert "guaranteed returns" in safe_response
    assert "Warnings:" in safe_response
    assert "Disclaimer:" in safe_response


def test_safety_engine_confidence_levels():
    engine = SafetyEngine()
    sparse_response = "Invest maybe."
    sparse_res = engine.calculate_confidence(sparse_response, {})
    assert sparse_res["level"] in ("low", "medium")

    detailed_response = (
        "Allocating ₹25,000 per month into an equity mutual fund provides an estimated 12% annual return. "
        "Please consult a certified financial advisor to review your overall risk appetite."
    )
    context = {"income": 1500000, "expenses": 800000}
    rich_res = engine.calculate_confidence(detailed_response, context)
    assert rich_res["score"] > sparse_res["score"]
