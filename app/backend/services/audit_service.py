"""Audit logging service for platform admin actions."""
import json
from sqlalchemy.orm import Session
from app.backend.models.db_models import AuditLog, User


def log_audit(
    db: Session,
    *,
    actor: User,
    action: str,
    resource_type: str,
    resource_id: int = None,
    details: dict = None,
    ip_address: str = None,
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
    """
    entry = AuditLog(
        actor_user_id=actor.id,
        actor_email=actor.email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details or {}),
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    return entry
