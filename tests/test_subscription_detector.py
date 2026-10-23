"""
Unit tests for Subscription & Recurring Expense Detection and Price Surge Radar.
"""

from datetime import date, timedelta
import pytest
from utils.subscription_detector import detect_subscriptions, _parse_date, update_subscription_status
from models import db, User, RecurringExpense, Expense


def test_parse_date_formats():
    assert _parse_date("2026-09-15") == date(2026, 9, 15)
    assert _parse_date("2026-09-15 12:30:00") == date(2026, 9, 15)
    assert _parse_date(date(2026, 9, 15)) == date(2026, 9, 15)
    assert _parse_date("invalid-date") is None


def test_detect_subscriptions_monthly_cadence():
    expenses = [
        {"merchant": "Netflix", "category": "Entertainment", "amount": 649.0, "date": "2026-07-01"},
        {"merchant": "Netflix", "category": "Entertainment", "amount": 649.0, "date": "2026-08-01"},
        {"merchant": "Netflix", "category": "Entertainment", "amount": 649.0, "date": "2026-09-01"},
    ]
    detected = detect_subscriptions(expenses)
    assert len(detected) == 1
    sub = detected[0]
    assert sub["merchant"] == "Netflix"
    assert sub["frequency"] == "monthly"
    assert sub["amount"] == 649.0
    assert sub["confidence"] == "high"
    assert sub["price_change"] is None


def test_detect_subscriptions_price_surge():
    expenses = [
        {"merchant": "Spotify", "category": "Music", "amount": 119.0, "date": "2026-07-10"},
        {"merchant": "Spotify", "category": "Music", "amount": 119.0, "date": "2026-08-10"},
        {"merchant": "Spotify", "category": "Music", "amount": 149.0, "date": "2026-09-10"},
    ]
    detected = detect_subscriptions(expenses)
    assert len(detected) == 1
    sub = detected[0]
    assert sub["merchant"] == "Spotify"
    assert sub["amount"] == 149.0
    assert sub["price_change"] is not None
    assert sub["price_change"]["is_surge"] is True
    assert sub["price_change"]["previous_amount"] == 119.0
    assert sub["price_change"]["latest_amount"] == 149.0
    assert sub["price_change"]["percent_change"] > 20.0


def test_detect_subscriptions_empty_or_single():
    assert detect_subscriptions([]) == []
    single = [{"merchant": "Gym", "category": "Fitness", "amount": 2000.0, "date": "2026-09-01"}]
    assert detect_subscriptions(single) == []
