"""Team invite email delivery — shared by onboarding and team routes."""
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.backend.models.db_models import PasswordResetToken, User

logger = logging.getLogger(__name__)

INVITE_TOKEN_EXPIRE_HOURS = 72


def send_team_invite_email(
    db: Session,
    *,
    invitee: User,
    inviter_name: str,
    tenant_name: str,
    tenant_slug: str,
) -> bool:
    """Create a set-password token and email the invitee. Returns True if sent."""
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == invitee.id).delete()

    reset_token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        user_id=invitee.id,
        token=reset_token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=INVITE_TOKEN_EXPIRE_HOURS),
    ))
    db.flush()

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    reset_url = f"{frontend_url}/reset-password/{reset_token}"
    login_url = f"{frontend_url}/login?workspace={tenant_slug}"

    html_body = (
        f"<h2>You've been invited to {tenant_name} on ARIA</h2>"
        f"<p><strong>{inviter_name}</strong> invited you to join their workspace on "
        f"ARIA Resume Intelligence.</p>"
        f"<p>Set your password using the link below (valid for {INVITE_TOKEN_EXPIRE_HOURS} hours):</p>"
        f'<p><a href="{reset_url}">Set your password</a></p>'
        f"<p>Your workspace slug is <strong>{tenant_slug}</strong>. "
        f'Use it when signing in: <a href="{login_url}">{login_url}</a></p>'
        f"<hr><p style='color:gray;font-size:12px;'>"
        f"This is an automated message from ARIA Resume Intelligence.</p>"
    )

    try:
        from app.backend.services.email_service import email_service, get_tenant_email_service
        tenant_svc = get_tenant_email_service(db, invitee.tenant_id)
        svc = tenant_svc or __import__(
            "app.backend.services.email_service", fromlist=["email_service"]
        ).email_service
        return svc.send_email(
            invitee.email,
            f"Join {tenant_name} on ARIA — Set Your Password",
            html_body,
        )
    except Exception as exc:
        logger.error("Failed to send team invite email to %s: %s", invitee.email, exc)
        return False
