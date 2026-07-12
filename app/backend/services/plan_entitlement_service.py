"""Plan limits and feature entitlements — single source of truth per tenant."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.backend.models.db_models import SubscriptionPlan, Tenant, User

# Feature keys that can be gated via plan limits JSON and/or plan_features table.
GATED_FEATURE_KEYS = frozenset({
    "video_analysis",
    "batch_analysis",
    "custom_weights",
    "api_access",
    "export_excel",
    "transcript_analysis",
    "email_generation",
    "requisitions",
    "pipeline",
    "compare",
    "analytics",
    "ai_interviews",
    "white_label",
    "hm_workflow",
    "sso",
    "priority_support",
    "dedicated_support",
    "custom_integrations",
})

# Maps limit JSON keys that differ from feature flag keys.
_LIMIT_FEATURE_ALIASES = {
    "batch_analysis": "batch_size",
}


def parse_plan_limits(plan: Optional[SubscriptionPlan]) -> Dict[str, Any]:
    if not plan or not plan.limits:
        return {}
    try:
        data = json.loads(plan.limits)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


DEFAULT_PLAN_NAMES = ("starter", "free")


def get_tenant_plan(db: Session, tenant_id: int) -> Optional[SubscriptionPlan]:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return None
    if tenant.plan_id:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == tenant.plan_id).first()
        if plan:
            return plan
    return db.query(SubscriptionPlan).filter(
        SubscriptionPlan.name.in_(DEFAULT_PLAN_NAMES),
        SubscriptionPlan.is_active == True,
    ).first()


def get_default_plan(db: Session) -> Optional[SubscriptionPlan]:
    """Resolve the default (starter/free) subscription plan."""
    return db.query(SubscriptionPlan).filter(
        SubscriptionPlan.name.in_(DEFAULT_PLAN_NAMES),
        SubscriptionPlan.is_active == True,
    ).order_by(SubscriptionPlan.sort_order).first()


def resolve_plan_by_name(db: Session, *names: str) -> Optional[SubscriptionPlan]:
    """Look up a plan by one of several names (supports legacy aliases)."""
    return db.query(SubscriptionPlan).filter(
        SubscriptionPlan.name.in_(names),
        SubscriptionPlan.is_active == True,
    ).first()


def get_tenant_limits(db: Session, tenant_id: int) -> Dict[str, Any]:
    return parse_plan_limits(get_tenant_plan(db, tenant_id))


def _limit_allows_feature(limits: Dict[str, Any], feature_key: str) -> Optional[bool]:
    """Return True/False if limits explicitly define this feature, else None."""
    if feature_key in limits and isinstance(limits[feature_key], bool):
        return limits[feature_key]

    if feature_key == "batch_analysis":
        batch_size = limits.get("batch_size", 1)
        try:
            return int(batch_size) > 1
        except (TypeError, ValueError):
            return False

    alias = _LIMIT_FEATURE_ALIASES.get(feature_key)
    if alias and alias in limits:
        val = limits[alias]
        if isinstance(val, bool):
            return val
        if alias == "batch_size":
            try:
                return int(val) > 1
            except (TypeError, ValueError):
                return False
    return None


def tenant_has_feature(db: Session, tenant_id: int, feature_key: str) -> bool:
    """Check plan limits JSON for a feature (used by feature_flag_service)."""
    limits = get_tenant_limits(db, tenant_id)
    allowed = _limit_allows_feature(limits, feature_key)
    if allowed is not None:
        return allowed
    # Unknown feature in limits — defer to plan_features / global flags.
    return True


def check_team_member_capacity(db: Session, tenant_id: int) -> tuple[bool, int, int]:
    """Return (allowed, current_count, limit)."""
    from app.backend.models.db_models import User as UserModel

    limits = get_tenant_limits(db, tenant_id)
    limit = int(limits.get("team_members", 1))
    count = (
        db.query(UserModel)
        .filter(UserModel.tenant_id == tenant_id, UserModel.is_active == True)
        .count()
    )
    if limit < 0:
        return True, count, limit
    return count < limit, count, limit


def get_batch_size_limit(db: Session, tenant_id: int) -> int:
    limits = get_tenant_limits(db, tenant_id)
    try:
        return int(limits.get("batch_size", 1))
    except (TypeError, ValueError):
        return 1


def plan_feature_detail(db: Session, tenant_id: int, feature_key: str) -> Dict[str, Any]:
    """Human-readable entitlement check for API errors."""
    from app.backend.services.feature_flag_service import is_feature_enabled

    enabled = is_feature_enabled(db, tenant_id, feature_key)
    limits = get_tenant_limits(db, tenant_id)
    plan = get_tenant_plan(db, tenant_id)
    return {
        "feature": feature_key,
        "enabled": enabled,
        "plan": plan.name if plan else None,
        "plan_display_name": (plan.display_name or plan.name) if plan else None,
        "upgrade_hint": _upgrade_hint(feature_key),
        "limits": limits,
    }


def _upgrade_hint(feature_key: str) -> str:
    hints = {
        "requisitions": "Upgrade to Growth or higher to use Requisitions.",
        "pipeline": "Upgrade to Growth or higher to use Pipeline.",
        "compare": "Upgrade to Growth or higher to compare candidates.",
        "analytics": "Upgrade to Agency or higher for Analytics.",
        "ai_interviews": "Upgrade to Business or higher for AI Interviews.",
        "video_analysis": "Upgrade to Business or higher for Video Analysis.",
        "api_access": "Upgrade to Agency or higher for API access.",
        "custom_weights": "Upgrade to Business or higher for custom scoring weights.",
        "white_label": "Upgrade to Business or higher for white-label branding.",
        "hm_workflow": "Upgrade to Growth or higher for Hiring Manager workflows.",
        "export_excel": "Upgrade to Growth or higher to export data.",
        "batch_analysis": "Upgrade to Growth or higher for batch screening.",
    }
    return hints.get(feature_key, "Upgrade your plan to access this feature.")
