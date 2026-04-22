"""
Email notification service for admin alerts.

Supports quota warnings, subscription expiry notices, and suspension
notifications.  Uses smtplib for delivery with graceful degradation
when SMTP is not configured.
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Sends admin notification emails via SMTP.

    Configuration is read from environment variables so no secrets are
    hard-coded.  When SMTP_HOST or SMTP_FROM are missing the service
    degrades gracefully — every public method returns ``False`` and
    logs a warning instead of raising.
    """

    def __init__(self) -> None:
        self.smtp_host: Optional[str] = os.getenv("SMTP_HOST")
        self.smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user: Optional[str] = os.getenv("SMTP_USER")
        self.smtp_password: Optional[str] = os.getenv("SMTP_PASSWORD")
        self.smtp_from: Optional[str] = os.getenv("SMTP_FROM")

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_configured(self) -> bool:
        """Return ``True`` when the minimum SMTP settings are present."""
        return bool(self.smtp_host and self.smtp_from)

    # ── Core send ─────────────────────────────────────────────────────────────

    def send_email(self, to: str, subject: str, body_html: str) -> bool:
        """Send an HTML email to *to*.

        Returns ``True`` on success, ``False`` on failure (including
        the case where SMTP is not configured).
        """
        if not self.is_configured:
            logger.warning(
                "Email not sent — SMTP not configured (SMTP_HOST=%s, SMTP_FROM=%s)",
                self.smtp_host,
                self.smtp_from,
            )
            return False

        msg = MIMEMultipart("alternative")
        msg["From"] = self.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body_html, "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_from, to, msg.as_string())
            logger.info("Email sent to %s: %s", to, subject)
            return True
        except Exception:
            logger.exception("Failed to send email to %s: %s", to, subject)
            return False

    # ── Template helpers ──────────────────────────────────────────────────────

    def send_quota_warning(
        self, tenant_name: str, admin_email: str, usage_pct: int
    ) -> bool:
        """Notify an admin that their tenant is approaching its quota."""
        body = (
            f"<h2>Quota Warning — {tenant_name}</h2>"
            f"<p>Your tenant <strong>{tenant_name}</strong> has reached "
            f"<strong>{usage_pct}%</strong> of its monthly analysis quota.</p>"
            f"<p>Please consider upgrading your plan or reducing usage to avoid "
            f"service interruptions.</p>"
            f"<hr><p style='color:gray;font-size:12px;'>"
            f"This is an automated message from ARIA Resume Intelligence.</p>"
        )
        return self.send_email(
            to=admin_email,
            subject=f"Quota Warning: {tenant_name} at {usage_pct}% usage",
            body_html=body,
        )

    def send_subscription_expiry(
        self, tenant_name: str, admin_email: str, days_remaining: int
    ) -> bool:
        """Notify an admin that their subscription is expiring soon."""
        body = (
            f"<h2>Subscription Expiring — {tenant_name}</h2>"
            f"<p>Your subscription for <strong>{tenant_name}</strong> expires in "
            f"<strong>{days_remaining} day{'s' if days_remaining != 1 else ''}</strong>.</p>"
            f"<p>Please renew your subscription to maintain uninterrupted access.</p>"
            f"<hr><p style='color:gray;font-size:12px;'>"
            f"This is an automated message from ARIA Resume Intelligence.</p>"
        )
        return self.send_email(
            to=admin_email,
            subject=f"Subscription Expiring: {tenant_name} — {days_remaining} day{'s' if days_remaining != 1 else ''} remaining",
            body_html=body,
        )

    def send_suspension_notice(
        self, tenant_name: str, admin_email: str, reason: str
    ) -> bool:
        """Notify an admin that their tenant has been suspended."""
        body = (
            f"<h2>Account Suspended — {tenant_name}</h2>"
            f"<p>Your tenant <strong>{tenant_name}</strong> has been suspended.</p>"
            f"<p><strong>Reason:</strong> {reason}</p>"
            f"<p>Please contact support if you believe this is an error.</p>"
            f"<hr><p style='color:gray;font-size:12px;'>"
            f"This is an automated message from ARIA Resume Intelligence.</p>"
        )
        return self.send_email(
            to=admin_email,
            subject=f"Account Suspended: {tenant_name}",
            body_html=body,
        )


# Module-level singleton for convenience
email_service = EmailService()
