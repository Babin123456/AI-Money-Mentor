"""
Subscription and Recurring Expense Detector with Price Surge Radar.
Identifies recurring patterns, calculates projected next due dates,
enforces user-tenant isolation, and flags subscription price increases.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any
from models import db, RecurringExpense, Expense


def _parse_date(date_val: Any) -> Optional[date]:
    """Robustly parse date from date, datetime, or varied string formats."""
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, date):
        return date_val
    if isinstance(date_val, str):
        cleaned = date_val.strip()
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
    return None


def detect_subscriptions(transactions: List[Any]) -> List[Dict]:
    """Detect subscription-like recurring expenses and price increases.
    
    Args:
        transactions: List of Expense model instances or dictionaries.
        
    Returns:
        List of detected subscription metadata dicts.
    """
    patterns: Dict[str, Dict] = {}
    
    for exp in transactions:
        merchant = (
            getattr(exp, "merchant_name", None)
            or getattr(exp, "merchant", None)
            or (exp.get("merchant_name") if isinstance(exp, dict) else None)
            or (exp.get("merchant") if isinstance(exp, dict) else None)
            or "Unknown"
        )
        category = getattr(exp, "category", None) or (exp.get("category") if isinstance(exp, dict) else "General")
        amount = getattr(exp, "amount", None) or (exp.get("amount") if isinstance(exp, dict) else 0.0)
        date_raw = getattr(exp, "date", None) or (exp.get("date") if isinstance(exp, dict) else None)
        
        parsed_date = _parse_date(date_raw)
        if parsed_date is None or not amount or float(amount) <= 0:
            continue
            
        key = f"{str(merchant).strip().lower()}_{str(category).strip().lower()}"
        if key not in patterns:
            patterns[key] = {
                "merchant": merchant,
                "category": category,
                "entries": []
            }
        patterns[key]["entries"].append({
            "amount": float(amount),
            "date": parsed_date
        })
        
    detected: List[Dict] = []
    
    for key, data in patterns.items():
        entries = sorted(data["entries"], key=lambda x: x["date"])
        if len(entries) < 2:
            continue
            
        amounts = [e["amount"] for e in entries]
        dates = [e["date"] for e in entries]
        avg_amount = sum(amounts) / len(amounts)
        
        # Check price surge / change between consecutive payments
        price_change = None
        if len(entries) >= 2:
            prev_amt = entries[-2]["amount"]
            latest_amt = entries[-1]["amount"]
            if abs(latest_amt - prev_amt) >= 1.0:
                pct = ((latest_amt - prev_amt) / prev_amt) * 100
                price_change = {
                    "previous_amount": round(prev_amt, 2),
                    "latest_amount": round(latest_amt, 2),
                    "difference": round(latest_amt - prev_amt, 2),
                    "percent_change": round(pct, 1),
                    "is_surge": pct > 0
                }
        
        # Calculate recurrence cadence
        diffs = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        avg_diff = sum(diffs) / len(diffs)
        
        frequency = "unknown"
        if 25 <= avg_diff <= 33:
            frequency = "monthly"
        elif 6 <= avg_diff <= 9:
            frequency = "weekly"
        elif 13 <= avg_diff <= 17:
            frequency = "bi-weekly"
        elif 80 <= avg_diff <= 100:
            frequency = "quarterly"
        elif 350 <= avg_diff <= 375:
            frequency = "yearly"
            
        if frequency != "unknown":
            next_due = dates[-1] + timedelta(days=round(avg_diff))
            detected.append({
                "merchant": data["merchant"],
                "category": data["category"],
                "amount": round(amounts[-1], 2),  # Use latest known billing amount
                "average_amount": round(avg_amount, 2),
                "frequency": frequency,
                "next_due": next_due.isoformat(),
                "confidence": "high" if len(amounts) >= 3 else "medium",
                "sample_count": len(amounts),
                "price_change": price_change
            })
            
    return detected


def run_detection(user_id: Optional[int] = None) -> Dict:
    """Run subscription detection on recent expenses with strict user scoping.
    
    Persists newly identified patterns to RecurringExpense marked as pending.
    """
    cutoff_date = date.today() - timedelta(days=90)
    
    query = Expense.query.filter(Expense.date >= cutoff_date.isoformat())
    if user_id is not None:
        query = query.filter(Expense.user_id == user_id)
        
    expenses = query.all()
    detected = detect_subscriptions(expenses)
    
    persisted_count = 0
    surges_count = 0
    
    for sub in detected:
        if sub.get("price_change") and sub["price_change"].get("is_surge"):
            surges_count += 1
            
        due_dt = _parse_date(sub["next_due"])
        if not due_dt:
            continue
            
        filter_kwargs = {
            "merchant": sub["merchant"],
            "category": sub["category"]
        }
        if user_id is not None:
            filter_kwargs["user_id"] = user_id
            
        existing = RecurringExpense.query.filter_by(**filter_kwargs).first()
        if not existing:
            rec = RecurringExpense(
                user_id=user_id or 1,
                amount=sub["amount"],
                category=sub["category"],
                merchant=sub["merchant"],
                frequency=sub["frequency"],
                start_date=due_dt,
                next_due_date=due_dt,
                is_subscription=True,
                status="pending",
                last_price=sub["price_change"]["previous_amount"] if sub.get("price_change") else sub["amount"],
                auto_add=False,
                is_active=True
            )
            db.session.add(rec)
            persisted_count += 1
        else:
            # Update last price tracking if price changed
            if sub.get("price_change"):
                existing.last_price = sub["price_change"]["previous_amount"]
                existing.amount = sub["amount"]
                
    db.session.commit()
    return {
        "success": True,
        "detected": detected,
        "count": len(detected),
        "newly_added": persisted_count,
        "price_surges_count": surges_count
    }


def update_subscription_status(subscription_id: int, user_id: int, status: str) -> Dict:
    """Update subscription state (active, paused, canceled, ignored) safely."""
    allowed = {"active", "paused", "canceled", "ignored"}
    if status not in allowed:
        return {"success": False, "error": f"Invalid status: {status}"}
        
    sub = RecurringExpense.query.filter_by(id=subscription_id, user_id=user_id).first()
    if not sub:
        return {"success": False, "error": "Subscription not found"}
        
    sub.status = status
    sub.is_active = (status == "active")
    db.session.commit()
    return {"success": True, "subscription": sub.to_dict()}
