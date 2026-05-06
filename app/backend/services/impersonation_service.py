"""Admin impersonation service for support and debugging."""
import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session

from app.backend.models.db_models import ImpersonationSession, User

logger = logging.getLogger(__name__)

DEFAULT_TTL_MINUTES = 15


def create_impersonation_session(
    db: Session,
    admin_user_id: int,
    target_user_id: int,
    ip_address: Optional[str] = None,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
) -> str:
    """Create a new impersonation session and return the raw token (shown once)."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

    session = ImpersonationSession(
        admin_user_id=admin_user_id,
        target_user_id=target_user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info("Impersonation session created: admin=%s target=%s expires=%s", admin_user_id, target_user_id, expires_at)
    return raw_token


def validate_impersonation_token(db: Session, raw_token: str) -> Optional[ImpersonationSession]:
    """Validate a raw impersonation token and return the session if valid."""
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    session = (
        db.query(ImpersonationSession)
        .filter(
            ImpersonationSession.token_hash == token_hash,
            ImpersonationSession.revoked_at.is_(None),
            ImpersonationSession.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )
    return session


def revoke_impersonation_session(db: Session, raw_token: str) -> bool:
    """Revoke an impersonation session by raw token."""
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    session = (
        db.query(ImpersonationSession)
        .filter(
            ImpersonationSession.token_hash == token_hash,
            ImpersonationSession.revoked_at.is_(None),
        )
        .first()
    )
    if not session:
        return False

    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Impersonation session revoked: id=%s admin=%s target=%s", session.id, session.admin_user_id, session.target_user_id)
    return True


def revoke_impersonation_session_by_id(db: Session, session_id: int) -> bool:
    """Revoke an impersonation session by ID."""
    session = db.query(ImpersonationSession).filter(ImpersonationSession.id == session_id).first()
    if not session or session.revoked_at is not None:
        return False

    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Impersonation session revoked by id: id=%s", session_id)
    return True


def list_active_sessions(
    db: Session,
    admin_user_id: Optional[int] = None,
) -> List[ImpersonationSession]:
    """List active (non-revoked, non-expired) impersonation sessions."""
    query = db.query(ImpersonationSession).filter(
        ImpersonationSession.revoked_at.is_(None),
        ImpersonationSession.expires_at > datetime.now(timezone.utc),
    )
    if admin_user_id is not None:
        query = query.filter(ImpersonationSession.admin_user_id == admin_user_id)

    return query.order_by(ImpersonationSession.created_at.desc()).all()


def get_session_by_id(db: Session, session_id: int) -> Optional[ImpersonationSession]:
    """Get a session by ID."""
    return db.query(ImpersonationSession).filter(ImpersonationSession.id == session_id).first()
