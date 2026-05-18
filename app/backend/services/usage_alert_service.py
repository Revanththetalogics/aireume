"""
Usage alert service — checks usage thresholds and dispatches notifications.

Alerts are fired at 80% and 100% of each plan limit.  Duplicate alerts are
prevented within the same billing period via a unique constraint on
(tenant_id, alert_type, period_key).
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.backend.models.db_models import UsageAlert, Tenant

log = logging.getLogger(__name__)


class UsageAlertService:
    """Checks usage against plan limits and sends threshold alerts."""

    THRESHOLDS = [80, 100]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_and_alert(
        self,
        db: Session,
        tenant_id: int,
        metric_name: str,
        current_value: int,
        limit_value: int,
    ) -> list[UsageAlert]:
        """Check if usage has crossed a threshold and send alerts if not already sent.

        Called after each usage increment.  Returns list of newly created
        alerts (may be empty).
        """
        # Skip for unlimited plans (limit = -1) or zero limits
        if limit_value is None or limit_value <= 0:
            return []

        created_alerts: list[UsageAlert] = []
        percent_used = int((current_value / limit_value) * 100)

        period_key = self._current_period_key()

        for threshold in self.THRESHOLDS:
            if percent_used < threshold:
                continue

            alert_type = f"{metric_name}_{threshold}"

            # Check if alert already sent this period
            existing = (
                db.query(UsageAlert)
                .filter(
                    UsageAlert.tenant_id == tenant_id,
                    UsageAlert.alert_type == alert_type,
                    UsageAlert.period_key == period_key,
                )
                .first()
            )
            if existing:
                continue

            alert = UsageAlert(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                alert_type=alert_type,
                threshold_percent=threshold,
                metric_name=metric_name,
                current_value=current_value,
                limit_value=limit_value,
                period_key=period_key,
                notified_at=datetime.now(timezone.utc),
            )
            db.add(alert)
            created_alerts.append(alert)

        if created_alerts:
            try:
                db.commit()
                # Dispatch notifications for each new alert
                tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
                if tenant:
                    for alert in created_alerts:
                        self._dispatch_alert(db, tenant, alert)
            except Exception:
                db.rollback()
                log.exception("Failed to commit usage alerts for tenant %d", tenant_id)

        return created_alerts

    def get_tenant_alerts(
        self, db: Session, tenant_id: int, limit: int = 20
    ) -> list[dict]:
        """Get recent usage alerts for a tenant, newest first."""
        alerts = (
            db.query(UsageAlert)
            .filter(UsageAlert.tenant_id == tenant_id)
            .order_by(UsageAlert.notified_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": a.id,
                "alert_type": a.alert_type,
                "threshold_percent": a.threshold_percent,
                "metric_name": a.metric_name,
                "current_value": a.current_value,
                "limit_value": a.limit_value,
                "notified_at": a.notified_at.isoformat() if a.notified_at else None,
                "period_key": a.period_key,
            }
            for a in alerts
        ]

    # ------------------------------------------------------------------
    # Notification dispatch
    # ------------------------------------------------------------------

    def _dispatch_alert(
        self, db: Session, tenant: Tenant, alert: UsageAlert
    ) -> None:
        """Send the alert via available channels (webhook + email)."""
        # 1. Fire webhook event
        self._fire_webhook(db, tenant, alert)

        # 2. Send email if SMTP configured (best-effort)
        self._send_email_alert(tenant, alert)

    def _fire_webhook(self, db: Session, tenant: Tenant, alert: UsageAlert) -> None:
        """Fire usage.threshold_reached webhook event (fire-and-forget)."""
        try:
            from app.backend.services.webhook_service import dispatch_event_background

            payload = {
                "metric": alert.metric_name,
                "threshold_percent": alert.threshold_percent,
                "current_value": alert.current_value,
                "limit_value": alert.limit_value,
                "period": alert.period_key,
            }
            dispatch_event_background(
                None, tenant.id, "usage.threshold_reached", payload
            )
        except Exception:
            log.exception(
                "Failed to dispatch usage webhook for tenant %d", tenant.id
            )

    def _send_email_alert(self, tenant: Tenant, alert: UsageAlert) -> None:
        """Send usage threshold email to tenant admins (best-effort)."""
        try:
            from app.backend.services.email_service import (
                email_service,
                get_tenant_email_service,
            )

            # Find admin emails for this tenant
            from app.backend.models.db_models import User

            # We need a DB session to query users — grab from tenant's session
            db = Session.object_session(tenant)
            if db is None:
                return

            admins = (
                db.query(User)
                .filter(
                    User.tenant_id == tenant.id,
                    User.role == "admin",
                    User.is_active == True,
                )
                .all()
            )
            if not admins:
                # Fall back to any active user
                admins = (
                    db.query(User)
                    .filter(User.tenant_id == tenant.id, User.is_active == True)
                    .limit(3)
                    .all()
                )

            if not admins:
                return

            subject = (
                f"Usage Alert: {alert.metric_name} at {alert.threshold_percent}% "
                f"— {tenant.name}"
            )
            body_html = (
                f"<h2>Usage Threshold Reached — {tenant.name}</h2>"
                f"<p>Your usage for <strong>{alert.metric_name}</strong> has reached "
                f"<strong>{alert.threshold_percent}%</strong> of your plan limit.</p>"
                f"<ul>"
                f"<li>Current usage: <strong>{alert.current_value}</strong></li>"
                f"<li>Plan limit: <strong>{alert.limit_value}</strong></li>"
                f"<li>Period: <strong>{alert.period_key}</strong></li>"
                f"</ul>"
                f"<p>Please consider upgrading your plan to avoid service interruptions.</p>"
                f"<hr><p style='color:gray;font-size:12px;'>"
                f"This is an automated message from ARIA Resume Intelligence.</p>"
            )

            for admin in admins:
                # Try tenant-specific SMTP first, fall back to global
                tenant_svc = get_tenant_email_service(db, tenant.id)
                if tenant_svc:
                    tenant_svc.send_email(admin.email, subject, body_html)
                else:
                    email_service.send_email(admin.email, subject, body_html)

        except Exception:
            log.exception(
                "Failed to send usage alert email for tenant %d", tenant.id
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _current_period_key() -> str:
        """Return the current period key in YYYY-MM format."""
        now = datetime.now(timezone.utc)
        return f"{now.year}-{now.month:02d}"


# Module-level singleton
usage_alert_service = UsageAlertService()
