"""
Tenant-level RBAC — admin, recruiter (write), viewer (read-only).
"""
from fastapi import Depends, HTTPException, Response, status

from app.backend.middleware.auth import get_current_user, require_active_subscription
from app.backend.models.db_models import User

TENANT_ROLE_ADMIN = "admin"
TENANT_ROLE_RECRUITER = "recruiter"
TENANT_ROLE_VIEWER = "viewer"

WRITE_ROLES = {TENANT_ROLE_ADMIN, TENANT_ROLE_RECRUITER}


def get_tenant_role(user: User) -> str:
    """Normalized tenant role; unknown values default to recruiter."""
    role = (getattr(user, "role", None) or TENANT_ROLE_RECRUITER).strip().lower()
    if role not in {TENANT_ROLE_ADMIN, TENANT_ROLE_RECRUITER, TENANT_ROLE_VIEWER}:
        return TENANT_ROLE_RECRUITER
    return role


def can_write_tenant(user: User) -> bool:
    return get_tenant_role(user) in WRITE_ROLES


def is_tenant_admin(user: User) -> bool:
    return get_tenant_role(user) == TENANT_ROLE_ADMIN


def is_tenant_viewer(user: User) -> bool:
    return get_tenant_role(user) == TENANT_ROLE_VIEWER


def _role_forbidden(required_roles: list[str]) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "message": "Your account is read-only. Ask an admin to upgrade your role to recruiter.",
            "error_code": "ROLE_FORBIDDEN",
            "required_roles": required_roles,
        },
    )


def require_recruiter_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not can_write_tenant(current_user):
        raise _role_forbidden([TENANT_ROLE_ADMIN, TENANT_ROLE_RECRUITER])
    return current_user


def require_active_recruiter(
    current_user: User = Depends(require_recruiter_or_admin),
    response: Response = None,
) -> User:
    """Write access with active subscription (analyze, imports, etc.)."""
    return require_active_subscription(current_user, response)


def can_manage_role_template(user: User, template) -> bool:
    """Admins manage all reqs; recruiters manage reqs they created (or legacy unowned)."""
    if is_tenant_admin(user):
        return True
    if not can_write_tenant(user):
        return False
    owner_id = getattr(template, "created_by", None)
    return owner_id is None or owner_id == user.id


def require_role_template_manager(user: User, template) -> None:
    if not can_manage_role_template(user, template):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "You can only edit roles you created. Ask an admin for access.",
                "error_code": "ROLE_OWNERSHIP_FORBIDDEN",
            },
        )
