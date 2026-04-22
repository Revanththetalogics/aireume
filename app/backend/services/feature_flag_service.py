"""Feature flag service with in-memory caching."""
import time
import threading
from sqlalchemy.orm import Session
from app.backend.models.db_models import FeatureFlag, TenantFeatureOverride

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
    1. Check tenant-specific override
    2. Fall back to global flag state
    3. If flag doesn't exist, default to True (safe default)
    """
    ck = _cache_key(tenant_id, feature_key)
    cached = _get_cached(ck)
    if cached is not None:
        return cached

    # Check tenant override first
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

    # Fall back to global flag
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
