"""
Financial Data Export, Backup & Portability Engine.
Provides RFC-4180 compliant CSV export for expenses,
comprehensive multi-entity JSON data backup archives,
and sanitized/anonymized export capabilities for privacy compliance.
"""

from typing import Dict, Any, List, Optional
import csv
import io
import json
from datetime import datetime
from models import db, Expense, BudgetLimit, Asset, Liability, FinancialGoal, RecurringExpense


class FinancialDataExporter:
    """Exports personal finance records into portable CSV and JSON formats."""

    @staticmethod
    def export_expenses_csv(user_id: int) -> str:
        """
        Generate RFC-4180 compliant CSV string of all expenses for the user.
        """
        expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc()).all()
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header
        writer.writerow(["Expense ID", "Date", "Category", "Amount", "Currency", "Merchant/Description"])

        for exp in expenses:
            date_str = str(exp.date) if exp.date else ""
            desc = getattr(exp, "merchant_name", None) or getattr(exp, "description", "") or ""
            currency = getattr(exp, "currency", "INR") or "INR"

            writer.writerow([
                exp.id,
                date_str,
                exp.category or "Uncategorized",
                f"{float(exp.amount):.2f}" if exp.amount is not None else "0.00",
                currency,
                desc
            ])

        return output.getvalue()

    @staticmethod
    def export_full_backup_json(user_id: int, anonymize: bool = False) -> Dict[str, Any]:
        """
        Generate full hierarchical backup archive across expenses, budgets,
        assets, liabilities, goals, and recurring subscriptions.
        Supports anonymization for external auditing or advisor review.
        """
        expenses = Expense.query.filter_by(user_id=user_id).all()
        budgets = BudgetLimit.query.filter_by(user_id=user_id).all()
        assets = Asset.query.filter_by(user_id=user_id).all()
        liabilities = Liability.query.filter_by(user_id=user_id).all()
        goals = FinancialGoal.query.filter_by(user_id=user_id).all()
        recurring = RecurringExpense.query.filter_by(user_id=user_id).all()

        def sanitize_text(val: Optional[str]) -> str:
            if not val:
                return ""
            if anonymize:
                return "[REDACTED]"
            return str(val)

        expenses_data = []
        for e in expenses:
            desc = getattr(e, "merchant_name", None) or getattr(e, "description", None) or ""
            expenses_data.append({
                "id": e.id,
                "date": str(e.date) if e.date else None,
                "category": e.category,
                "amount": float(e.amount) if e.amount is not None else 0.0,
                "currency": getattr(e, "currency", "INR"),
                "merchant_description": sanitize_text(desc)
            })

        budgets_data = []
        for b in budgets:
            budgets_data.append({
                "id": b.id,
                "category": b.category,
                "limit_amount": float(b.limit_amount) if b.limit_amount is not None else 0.0,
                "currency": getattr(b, "currency", "INR")
            })

        assets_data = []
        for a in assets:
            assets_data.append({
                "id": a.id,
                "name": sanitize_text(a.name),
                "amount": float(a.amount) if a.amount is not None else 0.0,
                "currency": getattr(a, "currency", "INR"),
                "date": str(a.date) if getattr(a, "date", None) else None
            })

        liabilities_data = []
        for l in liabilities:
            liabilities_data.append({
                "id": l.id,
                "name": sanitize_text(l.name),
                "amount": float(l.amount) if l.amount is not None else 0.0,
                "currency": getattr(l, "currency", "INR"),
                "date": str(l.date) if getattr(l, "date", None) else None
            })

        goals_data = []
        for g in goals:
            title = getattr(g, "name", None) or getattr(g, "title", "Goal")
            goals_data.append({
                "id": g.id,
                "title": sanitize_text(title),
                "target_amount": float(g.target_amount) if getattr(g, "target_amount", None) is not None else 0.0,
                "current_amount": float(g.current_amount) if getattr(g, "current_amount", None) is not None else 0.0
            })

        recurring_data = []
        for r in recurring:
            recurring_data.append({
                "id": r.id,
                "merchant": sanitize_text(r.merchant),
                "amount": float(r.amount) if r.amount is not None else 0.0,
                "category": r.category,
                "frequency": r.frequency,
                "is_active": getattr(r, "is_active", True)
            })

        return {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "anonymized": anonymize,
            "entities": {
                "expenses": expenses_data,
                "budgets": budgets_data,
                "assets": assets_data,
                "liabilities": liabilities_data,
                "financial_goals": goals_data,
                "recurring_subscriptions": recurring_data
            },
            "record_counts": {
                "expenses": len(expenses_data),
                "budgets": len(budgets_data),
                "assets": len(assets_data),
                "liabilities": len(liabilities_data),
                "financial_goals": len(goals_data),
                "recurring_subscriptions": len(recurring_data)
            }
        }

    @staticmethod
    def get_export_summary(user_id: int) -> Dict[str, Any]:
        """Get fast entity counts for export modal preview."""
        exp_count = Expense.query.filter_by(user_id=user_id).count()
        budget_count = BudgetLimit.query.filter_by(user_id=user_id).count()
        asset_count = Asset.query.filter_by(user_id=user_id).count()
        liability_count = Liability.query.filter_by(user_id=user_id).count()
        goal_count = FinancialGoal.query.filter_by(user_id=user_id).count()
        recurring_count = RecurringExpense.query.filter_by(user_id=user_id).count()

        total_records = exp_count + budget_count + asset_count + liability_count + goal_count + recurring_count

        return {
            "total_records": total_records,
            "counts": {
                "expenses": exp_count,
                "budgets": budget_count,
                "assets": asset_count,
                "liabilities": liability_count,
                "financial_goals": goal_count,
                "recurring_subscriptions": recurring_count
            }
        }
