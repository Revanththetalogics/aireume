"""
JWT authentication dependency for FastAPI routes.
"""
import os
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from app.backend.db.database import get_db
from app.backend.models.db_models import User

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


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
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
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).options(joinedload(User.tenant)).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Check tenant suspension
    if user.tenant and getattr(user.tenant, 'suspended_at', None) is not None:
        if not getattr(user, 'is_platform_admin', False):
            raise HTTPException(status_code=403, detail="Account suspended. Contact support.")

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require platform-level admin access (cross-tenant privilege)."""
    if not getattr(current_user, 'is_platform_admin', False):
        raise HTTPException(status_code=403, detail="Platform admin access required")
    return current_user


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
