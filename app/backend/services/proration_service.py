"""Proration calculation service for mid-cycle plan changes."""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)


def calculate_proration(
    old_plan_price: int,  # cents
    new_plan_price: int,  # cents
    period_start: datetime,
    period_end: datetime,
    change_date: datetime = None,  # defaults to now
) -> Dict[str, Any]:
    """Calculate prorated amounts for mid-cycle plan changes.

    Args:
        old_plan_price: Price of the old plan in cents.
        new_plan_price: Price of the new plan in cents.
        period_start: Start of the current billing period (timezone-aware).
        period_end: End of the current billing period (timezone-aware).
        change_date: Date of the plan change (timezone-aware). Defaults to UTC now.

    Returns:
        Dictionary with proration details:
        {
            "credit_amount": int,      # cents - unused portion of old plan
            "charge_amount": int,      # cents - remaining portion of new plan
            "net_amount": int,         # cents - positive = charge, negative = credit
            "days_remaining": int,
            "days_total": int,
            "proration_factor": float,  # 0.0 to 1.0
            "skipped": bool,            # True if proration was skipped
            "skip_reason": str,         # Reason for skipping (if skipped)
        }
    """
    # Edge case: no period dates set (new subscription)
    if period_start is None or period_end is None:
        return {
            "credit_amount": 0,
            "charge_amount": 0,
            "net_amount": 0,
            "days_remaining": 0,
            "days_total": 0,
            "proration_factor": 0.0,
            "skipped": True,
            "skip_reason": "No billing period dates set",
        }

    # Ensure all datetimes are timezone-aware UTC
    def _to_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    period_start = _to_utc(period_start)
    period_end = _to_utc(period_end)

    if change_date is None:
        change_date = datetime.now(timezone.utc)
    change_date = _to_utc(change_date)

    # Calculate days first to catch zero-day periods
    days_total = (period_end - period_start).days
    if days_total <= 0:
        return {
            "credit_amount": 0,
            "charge_amount": 0,
            "net_amount": 0,
            "days_remaining": 0,
            "days_total": 0,
            "proration_factor": 0.0,
            "skipped": True,
            "skip_reason": "Invalid billing period (zero or negative duration)",
        }

    # Edge case: change date outside billing period
    if change_date < period_start:
        return {
            "credit_amount": 0,
            "charge_amount": 0,
            "net_amount": 0,
            "days_remaining": 0,
            "days_total": days_total,
            "proration_factor": 0.0,
            "skipped": True,
            "skip_reason": "Change date is before the current billing period",
        }

    if change_date >= period_end:
        return {
            "credit_amount": 0,
            "charge_amount": 0,
            "net_amount": 0,
            "days_remaining": 0,
            "days_total": days_total,
            "proration_factor": 0.0,
            "skipped": True,
            "skip_reason": "Change date is at or after the end of the current billing period",
        }

    days_remaining = (period_end - change_date).days
    if days_remaining < 0:
        days_remaining = 0

    # Ensure at least 1 day remaining if change_date < period_end
    if days_remaining == 0 and change_date < period_end:
        days_remaining = 1

    proration_factor = days_remaining / days_total

    # Calculate amounts (in cents) — round to nearest cent
    credit_amount = int(round(old_plan_price * proration_factor))
    charge_amount = int(round(new_plan_price * proration_factor))
    net_amount = charge_amount - credit_amount

    return {
        "credit_amount": credit_amount,
        "charge_amount": charge_amount,
        "net_amount": net_amount,
        "days_remaining": days_remaining,
        "days_total": days_total,
        "proration_factor": round(proration_factor, 6),
        "skipped": False,
        "skip_reason": None,
    }


def get_plan_price_for_period(plan, period_start: datetime, period_end: datetime) -> int:
    """Return the appropriate plan price based on billing cycle length.

    Uses yearly price if the period is >= 300 days, otherwise monthly price.
    """
    if period_start is None or period_end is None:
        return plan.price_monthly if plan.price_monthly else 0

    days = (period_end - period_start).days
    if days >= 300:
        return plan.price_yearly if plan.price_yearly is not None else plan.price_monthly
    return plan.price_monthly if plan.price_monthly is not None else 0
