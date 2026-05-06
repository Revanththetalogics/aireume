"""Feature flag service with in-memory caching."""
import time
import threading
from sqlalchemy.orm import Session
from app.backend.models.db_models import FeatureFlag, TenantFeatureOverride, PlanFeature, Tenant

# Simple TTL cache
_cache = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 60  # seconds


def _cache_key(tenant_id: int, feature_key: str) -> str:
    return f"{tenant_id}:{feature_key}"


def _get_cached(key: str):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and time.time() - entry["ts"] < _CACHE_TTL:
            return entry["val"]
    return None


def _set_cached(key: str, val: bool):
    with _cache_lock:
        _cache[key] = {"val": val, "ts": time.time()}


def invalidate_cache(tenant_id: int = None, feature_key: str = None):
    """Clear cache entries. If no args, clear all."""
    with _cache_lock:
        if tenant_id is None and feature_key is None:
            _cache.clear()
        else:
            keys_to_remove = []
            for k in _cache:
                if tenant_id and str(tenant_id) in k:
                    keys_to_remove.append(k)
                elif feature_key and feature_key in k:
                    keys_to_remove.append(k)
            for k in keys_to_remove:
                del _cache[k]


def is_feature_enabled(db: Session, tenant_id: int, feature_key: str) -> bool:
    """Check if a feature is enabled for a specific tenant.

    Resolution order:
    1. Check tenant-specific override (highest priority)
    2. Check plan entitlement (if plan says disabled, feature is hidden)
    3. Fall back to global flag state
    4. If flag doesn't exist, default to True (safe default)
    """
    ck = _cache_key(tenant_id, feature_key)
    cached = _get_cached(ck)
    if cached is not None:
        return cached

    # 1. Check tenant-specific override
    override = (
        db.query(TenantFeatureOverride)
        .join(FeatureFlag)
        .filter(TenantFeatureOverride.tenant_id == tenant_id)
        .filter(FeatureFlag.key == feature_key)
        .first()
    )
    if override is not None:
        _set_cached(ck, override.enabled)
        return override.enabled

    # 2. Check plan entitlement
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant and tenant.plan_id is not None:
        plan_feature = (
            db.query(PlanFeature)
            .join(FeatureFlag)
            .filter(PlanFeature.plan_id == tenant.plan_id)
            .filter(FeatureFlag.key == feature_key)
            .first()
        )
        if plan_feature is not None:
            _set_cached(ck, plan_feature.enabled)
            return plan_feature.enabled

    # 3. Fall back to global flag
    flag = db.query(FeatureFlag).filter(FeatureFlag.key == feature_key).first()
    if flag is None:
        # Unknown flag — default to enabled (safe)
        _set_cached(ck, True)
        return True

    _set_cached(ck, flag.enabled_globally)
    return flag.enabled_globally


def get_all_flags(db: Session) -> list:
    """Get all feature flags."""
    return db.query(FeatureFlag).order_by(FeatureFlag.key).all()


def get_tenant_overrides(db: Session, tenant_id: int) -> list:
    """Get all feature overrides for a tenant."""
    return (
        db.query(TenantFeatureOverride)
        .filter(TenantFeatureOverride.tenant_id == tenant_id)
        .all()
    )


def get_plan_features(db: Session, plan_id: int) -> list:
    """Get all plan-feature mappings for a subscription plan."""
    return (
        db.query(PlanFeature)
        .filter(PlanFeature.plan_id == plan_id)
        .all()
    )


def get_enabled_features_for_tenant(db: Session, tenant_id: int) -> list:
    """Return a list of feature keys enabled for the tenant's current plan.

    This is useful for the frontend to know which features to show/hide.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant or not tenant.plan_id:
        return []

    flags = db.query(FeatureFlag).all()
    enabled = []
    for flag in flags:
        if is_feature_enabled(db, tenant_id, flag.key):
            enabled.append(flag.key)
    return enabled
