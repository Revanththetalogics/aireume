"""
Hard quota enforcement utility for pre-analysis checks.

Checks a tenant's billed monthly analysis count against their plan limits
*before* any analysis work begins.  This is a read-only, side-effect-free
check — the actual usage increment is still handled by
``_check_and_increment_usage`` inside ``analyze.py``.
"""

from typing import Dict

from sqlalchemy.orm import Session

from app.backend.models.db_models import Tenant, SubscriptionPlan

# ─── Plan limits fallback (used when no SubscriptionPlan row exists) ──────────

PLAN_LIMITS: Dict[str, int] = {
    "starter": 30,
    "free": 10,
    "growth": 200,
    "basic": 100,
    "professional": 500,
    "pro": 100,
    "agency": 1000,
    "business": 500,
    "enterprise": -1,
    "unlimited": -1,
}


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

    The *used* count is ``tenant.analyses_count_this_month``, the same
    counter the subscription dashboard and analyze increment path use.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return {
            "allowed": False,
            "remaining": 0,
            "limit": 0,
            "used": 0,
            "plan": "starter",
        }

    # Determine plan name and limit
    plan_name = "starter"
    analyses_limit = PLAN_LIMITS["starter"]

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
                analyses_limit = limits.get("analyses_per_month", PLAN_LIMITS.get(plan_name, PLAN_LIMITS["starter"]))
            except Exception:
                analyses_limit = PLAN_LIMITS.get(plan_name, PLAN_LIMITS["starter"])

    used = tenant.analyses_count_this_month or 0

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
