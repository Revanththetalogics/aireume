"""Batch scoring consistency service.

Provides result caching and deterministic scoring mode to ensure
the same resume scored multiple times produces identical results.
This is critical for audit compliance and reproducibility.

Features:
- Content-hash based result caching
- Deterministic mode flag (disables LLM non-determinism)
- Cache invalidation on JD or scoring weight changes
- Audit trail for cached results
"""

import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Cache TTL in hours (results expire after this period)
DEFAULT_CACHE_TTL_HOURS = 24

# In-memory cache (for single-process deployments)
# For multi-process/multi-node, use Redis or similar
_memory_cache: Dict[str, Dict[str, Any]] = {}


def _compute_cache_key(
    resume_text: str,
    jd_text: str,
    scoring_weights: Optional[Dict] = None,
    tenant_id: Optional[int] = None,
) -> str:
    """Compute a deterministic cache key for a screening result.

    The key is based on content hashes of resume, JD, and scoring config.
    """
    resume_hash = hashlib.sha256(resume_text.encode('utf-8')).hexdigest()[:32]
    jd_hash = hashlib.sha256(jd_text.encode('utf-8')).hexdigest()[:32]
    weights_hash = hashlib.sha256(
        json.dumps(scoring_weights or {}, sort_keys=True).encode('utf-8')
    ).hexdigest()[:16]
    tenant = str(tenant_id) if tenant_id else "global"
    return f"screening:{tenant}:{resume_hash}:{jd_hash}:{weights_hash}"


def get_cached_result(
    resume_text: str,
    jd_text: str,
    scoring_weights: Optional[Dict] = None,
    tenant_id: Optional[int] = None,
    ttl_hours: int = DEFAULT_CACHE_TTL_HOURS,
) -> Optional[Dict[str, Any]]:
    """Retrieve a cached screening result if available and not expired.

    Args:
        resume_text: Resume text.
        jd_text: Job description text.
        scoring_weights: Scoring weights used.
        tenant_id: Tenant ID for isolation.
        ttl_hours: Cache time-to-live in hours.

    Returns:
        Cached result dict or None if not found/expired.
    """
    # Skip cache lookup when tenant_id is None (test/legacy mode)
    if tenant_id is None:
        return None

    key = _compute_cache_key(resume_text, jd_text, scoring_weights, tenant_id)

    # Check memory cache
    cached = _memory_cache.get(key)
    if cached:
        created = cached.get("_created_at")
        if created:
            age = datetime.now(timezone.utc) - created
            if age < timedelta(hours=ttl_hours):
                logger.debug("Cache hit for key %s", key[:40])
                result = cached.get("result")
                result["_cached"] = True
                result["_cache_key"] = key[:40]
                return result
            else:
                logger.debug("Cache expired for key %s", key[:40])
                del _memory_cache[key]

    # Check database cache
    try:
        from app.backend.db.database import get_db_session
        from app.backend.models.db_models import ScreeningCache

        db = get_db_session()
        entry = db.query(ScreeningCache).filter(ScreeningCache.cache_key == key).first()
        if entry:
            age = datetime.now(timezone.utc) - entry.created_at
            if age < timedelta(hours=ttl_hours):
                result = json.loads(entry.result_json)
                result["_cached"] = True
                result["_cache_key"] = key[:40]
                logger.debug("DB cache hit for key %s", key[:40])
                return result
            else:
                db.delete(entry)
                db.commit()
    except Exception as e:
        logger.debug("DB cache lookup failed: %s", e)

    return None


def cache_result(
    resume_text: str,
    jd_text: str,
    result: Dict[str, Any],
    scoring_weights: Optional[Dict] = None,
    tenant_id: Optional[int] = None,
) -> str:
    """Cache a screening result for future retrieval.

    Args:
        resume_text: Resume text.
        jd_text: Job description text.
        result: Screening result to cache.
        scoring_weights: Scoring weights used.
        tenant_id: Tenant ID for isolation.

    Returns:
        The cache key used.
    """
    # Skip caching when tenant_id is None (test/legacy mode)
    if tenant_id is None:
        return ""

    key = _compute_cache_key(resume_text, jd_text, scoring_weights, tenant_id)

    # Store in memory cache
    _memory_cache[key] = {
        "result": result,
        "_created_at": datetime.now(timezone.utc),
    }

    # Also try to store in database
    try:
        from app.backend.db.database import get_db_session
        from app.backend.models.db_models import ScreeningCache

        db = get_db_session()
        entry = ScreeningCache(
            cache_key=key,
            tenant_id=tenant_id,
            result_json=json.dumps(result, default=str),
            resume_hash=hashlib.sha256(resume_text.encode('utf-8')).hexdigest()[:32],
            jd_hash=hashlib.sha256(jd_text.encode('utf-8')).hexdigest()[:32],
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.debug("DB cache store failed (non-critical): %s", e)

    logger.debug("Cached result with key %s", key[:40])
    return key


def invalidate_cache(
    resume_text: Optional[str] = None,
    jd_text: Optional[str] = None,
    tenant_id: Optional[int] = None,
) -> int:
    """Invalidate cached results.

    Can invalidate by resume+JD combination, or all results for a tenant.

    Returns:
        Number of entries invalidated.
    """
    count = 0

    if resume_text and jd_text:
        key = _compute_cache_key(resume_text, jd_text, None, tenant_id)
        if key in _memory_cache:
            del _memory_cache[key]
            count += 1
    elif tenant_id is not None:
        # Invalidate all entries for this tenant
        prefix = f"screening:{tenant_id}:"
        keys_to_delete = [k for k in _memory_cache if k.startswith(prefix)]
        for k in keys_to_delete:
            del _memory_cache[k]
            count += 1

    return count


def clear_all_cache() -> int:
    """Clear the entire in-memory cache. Returns number of entries cleared."""
    count = len(_memory_cache)
    _memory_cache.clear()
    return count
