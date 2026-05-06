"""Security event logging and threat detection service."""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.models.db_models import SecurityEvent, User

logger = logging.getLogger(__name__)

# Event type constants
EVENT_LOGIN_SUCCESS = "login_success"
EVENT_LOGIN_FAILURE = "login_failure"
EVENT_PASSWORD_RESET_REQUESTED = "password_reset_requested"
EVENT_TOKEN_REVOKED = "token_revoked"
EVENT_IMPERSONATION_STARTED = "impersonation_started"
EVENT_IMPERSONATION_ENDED = "impersonation_ended"
EVENT_SUSPICIOUS_ACTIVITY = "suspicious_activity"


def record_event(
    db: Session,
    event_type: str,
    tenant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict] = None,
) -> SecurityEvent:
    """Record a generic security event."""
    event = SecurityEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type,
        ip_address=ip_address,
        user_agent=user_agent,
        details=json.dumps(details) if details else None,
    )
    db.add(event)
    db.commit()
    return event


def record_login_success(
    db: Session,
    user: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SecurityEvent:
    """Record a successful login event."""
    return record_event(
        db,
        event_type=EVENT_LOGIN_SUCCESS,
        tenant_id=user.tenant_id,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"email": user.email},
    )


def record_login_failure(
    db: Session,
    email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    reason: Optional[str] = None,
    tenant_id: Optional[int] = None,
) -> SecurityEvent:
    """Record a failed login attempt."""
    return record_event(
        db,
        event_type=EVENT_LOGIN_FAILURE,
        tenant_id=tenant_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"email": email, "reason": reason or "Invalid credentials"},
    )


def record_impersonation(
    db: Session,
    admin_id: int,
    target_id: int,
    ip_address: Optional[str] = None,
    started: bool = True,
) -> SecurityEvent:
    """Record impersonation start or end."""
    event_type = EVENT_IMPERSONATION_STARTED if started else EVENT_IMPERSONATION_ENDED
    return record_event(
        db,
        event_type=event_type,
        user_id=admin_id,
        ip_address=ip_address,
        details={"admin_id": admin_id, "target_id": target_id},
    )


def record_suspicious_activity(
    db: Session,
    ip_address: Optional[str] = None,
    email: Optional[str] = None,
    details: Optional[dict] = None,
) -> SecurityEvent:
    """Record a suspicious activity alert."""
    return record_event(
        db,
        event_type=EVENT_SUSPICIOUS_ACTIVITY,
        ip_address=ip_address,
        details={"email": email, **(details or {})},
    )


def is_suspicious(
    db: Session,
    ip_address: Optional[str] = None,
    email: Optional[str] = None,
    window_minutes: int = 30,
    threshold: int = 5,
) -> bool:
    """Check if login failures exceed threshold within the time window.

    Returns True if the IP or email has >= threshold login_failure events
    in the last window_minutes.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

    query = db.query(func.count(SecurityEvent.id)).filter(
        SecurityEvent.event_type == EVENT_LOGIN_FAILURE,
        SecurityEvent.created_at >= cutoff,
    )

    if ip_address:
        query = query.filter(SecurityEvent.ip_address == ip_address)
    elif email:
        # Details stores email in JSON; for simplicity we also check raw email
        # if we had it as a column. Here we do a LIKE on details for PostgreSQL/SQLite compat.
        query = query.filter(SecurityEvent.details.ilike(f'%"email": "{email}"%'))
    else:
        # Need at least one filter criteria
        return False

    count = query.scalar() or 0
    return count >= threshold


def get_security_events(
    db: Session,
    event_type: Optional[str] = None,
    tenant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Query security events with filters and pagination."""
    query = db.query(SecurityEvent).order_by(SecurityEvent.created_at.desc())

    if event_type:
        query = query.filter(SecurityEvent.event_type == event_type)
    if tenant_id is not None:
        query = query.filter(SecurityEvent.tenant_id == tenant_id)
    if user_id is not None:
        query = query.filter(SecurityEvent.user_id == user_id)
    if ip_address:
        query = query.filter(SecurityEvent.ip_address == ip_address)
    if date_from:
        query = query.filter(SecurityEvent.created_at >= date_from)
    if date_to:
        query = query.filter(SecurityEvent.created_at <= date_to)

    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return items, total
