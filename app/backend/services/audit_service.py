"""Audit logging services — platform admin audit trail + field-level change tracking."""

import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.backend.models.db_models import AuditLog, FieldAuditLog, User


def _hash_entry(prev_hash: str, actor_email: str, action: str, details: str) -> str:
    payload = f"{prev_hash}|{actor_email}|{action}|{details}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log_audit(
    db: Session,
    *,
    actor: User,
    action: str,
    resource_type: str,
    resource_id: int = None,
    details: dict = None,
    ip_address: str = None,
    tenant_id: int = None,
):
    """Record an audit log entry and persist it.

    Callers often ``commit()`` business changes before logging. ``get_db()``
    closes without a final commit, so this function must commit the hash-chained
    row or the audit trail is rolled back.
    """
    details_json = json.dumps(details or {}, sort_keys=True)
    impersonated_by = getattr(actor, "_impersonated_by", None)

    last = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    prev_hash = (last.entry_hash if last else None) or "genesis"
    entry_hash = _hash_entry(prev_hash, actor.email, action, details_json)
    entry = AuditLog(
        actor_user_id=actor.id,
        actor_email=actor.email,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details_json,
        ip_address=ip_address,
        entry_hash=entry_hash,
        prev_hash=prev_hash,
        impersonated_by=impersonated_by,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ─── Field-Level Change Tracking (Dynamic Reports) ──────────────────────────


def log_field_change(
    db: Session,
    tenant_id: int,
    entity_type: str,
    entity_id: int,
    field_name: str,
    old_value,
    new_value,
    user_id: int,
    reason: str = None,
):
    """Log a field-level change to the audit trail.

    Skips logging when old and new values are identical (string comparison).
    Does NOT commit — the caller is responsible for committing the transaction.
    """
    if str(old_value or "") == str(new_value or ""):
        return  # No actual change

    entry = FieldAuditLog(
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        changed_by=user_id,
        changed_at=datetime.now(timezone.utc),
        change_reason=reason,
    )
    db.add(entry)


# ─── Tenant-Scoped Audit (no auto-commit) ─────────────────────────────────────


def log_tenant_event(
    db: Session,
    *,
    actor: User,
    action: str,
    resource_type: str,
    resource_id: int = None,
    details: dict = None,
    ip_address: str = None,
):
    """Record a tenant-scoped audit event on the same hash chain as log_audit."""
    return log_audit(
        db,
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        tenant_id=actor.tenant_id,
    )
