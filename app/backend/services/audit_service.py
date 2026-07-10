"""Audit logging services — platform admin audit trail + field-level change tracking."""

import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.backend.models.db_models import AuditLog, FieldAuditLog, User


# ─── Platform Admin Audit Trail ─────────────────────────────────────────────


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
    """Record an audit log entry for a platform admin action.

    Args:
        db: Database session
        actor: The user performing the action
        action: Action identifier (e.g. "tenant.suspend", "plan.change")
        resource_type: Type of resource affected (e.g. "tenant", "user", "plan")
        resource_id: ID of the affected resource
        details: Optional JSON-serializable context dict
        ip_address: Optional IP address of the actor
        tenant_id: Optional tenant ID associated with the action
    """
    entry = AuditLog(
        actor_user_id=actor.id,
        actor_email=actor.email,
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details or {}),
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
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
    """Record a tenant-scoped audit event. Caller commits the transaction."""
    entry = AuditLog(
        actor_user_id=actor.id,
        actor_email=actor.email,
        tenant_id=actor.tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details or {}),
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
