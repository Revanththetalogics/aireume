"""
JWT authentication dependency for FastAPI routes.
"""
import hashlib
import os
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from app.backend.db.database import get_db
from app.backend.models.db_models import User, ImpersonationSession

_env = os.getenv("ENVIRONMENT", "development")
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    if _env == "production":
        raise RuntimeError("JWT_SECRET_KEY environment variable must be set in production")
    SECRET_KEY = "dev-secret-DO-NOT-USE-IN-PRODUCTION"
    import logging
    logging.getLogger(__name__).warning("Using default JWT secret — NOT safe for production")
ALGORITHM = "HS256"

bearer_scheme = HTTPBearer(auto_error=False)

# ─── Platform Role Constants ──────────────────────────────────────────────────

PLATFORM_ROLE_SUPER_ADMIN = "super_admin"
PLATFORM_ROLE_BILLING_ADMIN = "billing_admin"
PLATFORM_ROLE_SUPPORT = "support"
PLATFORM_ROLE_SECURITY_ADMIN = "security_admin"
PLATFORM_ROLE_READONLY = "readonly"

ALL_PLATFORM_ROLES = [
    PLATFORM_ROLE_SUPER_ADMIN,
    PLATFORM_ROLE_BILLING_ADMIN,
    PLATFORM_ROLE_SUPPORT,
    PLATFORM_ROLE_SECURITY_ADMIN,
    PLATFORM_ROLE_READONLY,
]

READ_PLATFORM_ROLES = [
    PLATFORM_ROLE_SUPER_ADMIN,
    PLATFORM_ROLE_BILLING_ADMIN,
    PLATFORM_ROLE_SUPPORT,
    PLATFORM_ROLE_SECURITY_ADMIN,
    PLATFORM_ROLE_READONLY,
]


# ─── User Loading ─────────────────────────────────────────────────────────────

def _load_user_from_token(db: Session, token: str) -> User:
    """Decode JWT and load user with tenant."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = (
        db.query(User)
        .options(joinedload(User.tenant))
        .filter(User.id == int(user_id), User.is_active == True)
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    # Try Authorization header first (for API clients)
    token = None
    if credentials is not None:
        token = credentials.credentials
    else:
        # Fall back to httpOnly cookie (for browser clients)
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = _load_user_from_token(db, token)

    # Check for impersonation token header
    impersonation_token = request.headers.get("X-Impersonation-Token")
    if impersonation_token:
        token_hash = hashlib.sha256(impersonation_token.encode()).hexdigest()
        session = (
            db.query(ImpersonationSession)
            .filter(
                ImpersonationSession.token_hash == token_hash,
                ImpersonationSession.revoked_at.is_(None),
                ImpersonationSession.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired impersonation session")

        # Load target user (the impersonated account)
        target_user = (
            db.query(User)
            .options(joinedload(User.tenant))
            .filter(User.id == session.target_user_id, User.is_active == True)
            .first()
        )
        if not target_user:
            raise HTTPException(status_code=401, detail="Impersonation target user not found")

        # Mark the request context so downstream code knows this is impersonated
        target_user._impersonated_by = session.admin_user_id
        target_user._impersonation_session_id = session.id
        user = target_user

    # Check tenant suspension (platform admins bypass)
    if user.tenant and getattr(user.tenant, "suspended_at", None) is not None:
        if not getattr(user, "is_platform_admin", False) and getattr(user, "platform_role", None) is None:
            raise HTTPException(status_code=403, detail="Account suspended. Contact support.")

    return user


# ─── Tenant-Level RBAC ────────────────────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ─── Platform-Level RBAC ──────────────────────────────────────────────────────

def _check_platform_role(current_user: User, allowed_roles: list[str]) -> User:
    """Internal helper to validate platform role."""
    user_role = getattr(current_user, "platform_role", None)
    legacy_flag = getattr(current_user, "is_platform_admin", False)

    # Backward compatibility: legacy is_platform_admin=true counts as super_admin
    if legacy_flag and PLATFORM_ROLE_SUPER_ADMIN in allowed_roles:
        return current_user

    if user_role in allowed_roles:
        return current_user

    raise HTTPException(status_code=403, detail="Platform admin access required")


def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require any platform-level admin access (backward compatible)."""
    return _check_platform_role(current_user, ALL_PLATFORM_ROLES)


def require_platform_role(roles: list[str]):
    """Generic decorator requiring one of the specified platform roles."""
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        return _check_platform_role(current_user, roles)
    return dependency


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    return _check_platform_role(current_user, [PLATFORM_ROLE_SUPER_ADMIN])


def require_billing_admin(current_user: User = Depends(get_current_user)) -> User:
    return _check_platform_role(current_user, [PLATFORM_ROLE_SUPER_ADMIN, PLATFORM_ROLE_BILLING_ADMIN])


def require_support(current_user: User = Depends(get_current_user)) -> User:
    return _check_platform_role(current_user, [PLATFORM_ROLE_SUPER_ADMIN, PLATFORM_ROLE_SUPPORT])


def require_security_admin(current_user: User = Depends(get_current_user)) -> User:
    return _check_platform_role(current_user, [PLATFORM_ROLE_SUPER_ADMIN, PLATFORM_ROLE_SECURITY_ADMIN])


def require_readonly_platform(current_user: User = Depends(get_current_user)) -> User:
    return _check_platform_role(current_user, READ_PLATFORM_ROLES)


# ─── Feature Gating ───────────────────────────────────────────────────────────

def require_feature(feature_key: str):
    """Dependency that checks if a feature is enabled for the current user's tenant."""
    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        from app.backend.services.feature_flag_service import is_feature_enabled
        if not is_feature_enabled(db, current_user.tenant_id, feature_key):
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{feature_key}' is not available on your plan"
            )
        return current_user
    return dependency
