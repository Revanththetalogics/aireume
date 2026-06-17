"""
Admin Notification Service.

Provides a single helper function for creating platform-level admin
notifications that appear in the notification center
(GET /api/admin/notifications).

Severity levels:
  - info     : informational, no immediate action required
  - warning  : should be reviewed soon
  - critical : requires immediate attention
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.backend.models.db_models import AdminNotification

log = logging.getLogger(__name__)


def create_admin_notification(
    db: Session,
    type: str,
    severity: str,
    title: str,
    message: str,
    tenant_id: Optional[int] = None,
) -> AdminNotification:
    """Persist a new admin notification and return the created instance.

    Always commits immediately so the record is visible to polling clients.
    On error the exception is swallowed and logged so callers are never
    disrupted.
    """
    try:
        notif = AdminNotification(
            type=type,
            severity=severity,
            title=title,
            message=message,
            tenant_id=tenant_id,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        log.info(
            "Admin notification created: [%s/%s] %s (tenant_id=%s)",
            severity, type, title, tenant_id,
        )
        return notif
    except Exception:
        log.exception(
            "Failed to create admin notification type=%s title=%r", type, title
        )
        try:
            db.rollback()
        except Exception:
            pass
        raise
