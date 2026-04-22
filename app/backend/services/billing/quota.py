"""
Hard quota enforcement utility for pre-analysis checks.

Checks a tenant's monthly screening-result count against their plan limits
*before* any analysis work begins.  This is a read-only, side-effect-free
check — the actual usage increment is still handled by
``_check_and_increment_usage`` inside ``analyze.py``.
"""

from datetime import datetime, timezone
from typing import Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.models.db_models import ScreeningResult, Tenant, SubscriptionPlan

# ─── Plan limits fallback (used when no SubscriptionPlan row exists) ──────────

PLAN_LIMITS: Dict[str, int] = {
    "free": 10,
    "basic": 100,
    "professional": 500,
    "pro": 100,        # alias — existing DB uses "pro" not "professional"
    "enterprise": -1,  # -1 = unlimited
    "unlimited": -1,
}


def _get_current_month_range() -> tuple[datetime, datetime]:
    """Return (start, end) for the current calendar month in UTC."""
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # End of month: first day of next month
    if now.month == 12:
        end = start.replace(year=now.year + 1, month=1)
    else:
        end = start.replace(month=now.month + 1)
    return start, end


def check_quota(tenant_id: int, db: Session) -> Dict:
    """Check whether the tenant is within their monthly analysis quota.

    Returns::

        {
            "allowed":   bool,
            "remaining": int,   # -1 when unlimited
            "limit":     int,   # -1 when unlimited
            "used":      int,
            "plan":      str,   # plan name or "free" as default
        }

    The *used* count is the number of ``screening_results`` rows created
    for this tenant in the current calendar month.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return {
            "allowed": False,
            "remaining": 0,
            "limit": 0,
            "used": 0,
            "plan": "free",
        }

    # Determine plan name and limit
    plan_name = "free"
    analyses_limit = PLAN_LIMITS["free"]

    if tenant.plan_id:
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == tenant.plan_id
        ).first()
        if plan:
            plan_name = plan.name
            # Try to read from the plan's JSON limits first
            try:
                import json as _json
                limits = _json.loads(plan.limits) if plan.limits else {}
                analyses_limit = limits.get("analyses_per_month", PLAN_LIMITS.get(plan_name, PLAN_LIMITS["free"]))
            except Exception:
                analyses_limit = PLAN_LIMITS.get(plan_name, PLAN_LIMITS["free"])

    # Count screening_results this calendar month
    start, end = _get_current_month_range()
    used = (
        db.query(func.count(ScreeningResult.id))
        .filter(
            ScreeningResult.tenant_id == tenant_id,
            ScreeningResult.timestamp >= start,
            ScreeningResult.timestamp < end,
        )
        .scalar() or 0
    )

    # Unlimited plans
    if analyses_limit < 0:
        return {
            "allowed": True,
            "remaining": -1,
            "limit": -1,
            "used": used,
            "plan": plan_name,
        }

    remaining = max(analyses_limit - used, 0)
    return {
        "allowed": used < analyses_limit,
        "remaining": remaining,
        "limit": analyses_limit,
        "used": used,
        "plan": plan_name,
    }
