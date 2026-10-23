import pytest
from flask import Flask
from models import db, User, Expense, BudgetLimit, FinancialGoal, Asset, Liability
from utils.data_exporter import FinancialDataExporter

@pytest.fixture
def app_with_db():
    test_app = Flask(__name__)
    test_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    test_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    test_app.config["TESTING"] = True

    db.init_app(test_app)
    with test_app.app_context():
        db.create_all()
        # Seed test user and records
        user = User(id=99, username="testuser", email="test@example.com", password_hash="dummy")
        db.session.add(user)

        exp1 = Expense(
            id=1,
            user_id=99,
            category="Food & Dining",
            amount=450.0,
            merchant_name="Starbucks Coffee",
            date="2026-10-20",
            currency="INR"
        )
        exp2 = Expense(
            id=2,
            user_id=99,
            category="Utilities",
            amount=1200.0,
            merchant_name="Electricity Bill",
            date="2026-10-15",
            currency="INR"
        )
        b1 = BudgetLimit(
            id=1,
            user_id=99,
            category="Food & Dining",
            limit_amount=5000.0,
            currency="INR"
        )
        g1 = FinancialGoal(
            id=1,
            user_id=99,
            name="Emergency Reserve",
            target_amount=100000.0,
            current_amount=25000.0,
            target_date="2027-01"
        )
        a1 = Asset(
            id=1,
            user_id=99,
            name="Emergency Savings Account",
            amount=50000.0,
            currency="INR"
        )
        l1 = Liability(
            id=1,
            user_id=99,
            name="Personal Loan",
            amount=30000.0,
            currency="INR"
        )

        db.session.add_all([exp1, exp2, b1, g1, a1, l1])
        db.session.commit()

        yield test_app
        db.session.remove()
        db.drop_all()

def test_export_expenses_csv(app_with_db):
    with app_with_db.app_context():
        csv_str = FinancialDataExporter.export_expenses_csv(user_id=99)
        lines = csv_str.strip().split("\r\n" if "\r\n" in csv_str else "\n")
        assert len(lines) >= 3  # Header + 2 expenses
        assert "Expense ID,Date,Category,Amount,Currency,Merchant/Description" in lines[0]
        assert "Starbucks Coffee" in csv_str
        assert "Electricity Bill" in csv_str
        assert "450.00" in csv_str

def test_export_full_backup_json(app_with_db):
    with app_with_db.app_context():
        backup = FinancialDataExporter.export_full_backup_json(user_id=99, anonymize=False)
        assert backup["version"] == "1.0"
        assert backup["anonymized"] is False
        assert "entities" in backup
        assert len(backup["entities"]["expenses"]) == 2
        assert len(backup["entities"]["budgets"]) == 1
        assert len(backup["entities"]["financial_goals"]) == 1
        assert len(backup["entities"]["assets"]) == 1
        assert len(backup["entities"]["liabilities"]) == 1
        descriptions = [e["merchant_description"] for e in backup["entities"]["expenses"]]
        assert "Starbucks Coffee" in descriptions

def test_export_anonymized_json(app_with_db):
    with app_with_db.app_context():
        backup = FinancialDataExporter.export_full_backup_json(user_id=99, anonymize=True)
        assert backup["anonymized"] is True
        for exp in backup["entities"]["expenses"]:
            assert exp["merchant_description"] == "[REDACTED]"
            assert "Starbucks" not in exp["merchant_description"]

def test_get_export_summary(app_with_db):
    with app_with_db.app_context():
        summary = FinancialDataExporter.get_export_summary(user_id=99)
        assert summary["total_records"] == 6
        assert summary["counts"]["expenses"] == 2
        assert summary["counts"]["budgets"] == 1
        assert summary["counts"]["financial_goals"] == 1
        assert summary["counts"]["assets"] == 1
        assert summary["counts"]["liabilities"] == 1
