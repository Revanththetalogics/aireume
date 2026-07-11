"""
Tenant-level RBAC — admin, recruiter, viewer, hiring_manager.
"""
from fastapi import Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.backend.middleware.auth import get_current_user, require_active_subscription
from app.backend.models.db_models import Requisition, User

TENANT_ROLE_ADMIN = "admin"
TENANT_ROLE_RECRUITER = "recruiter"
TENANT_ROLE_VIEWER = "viewer"
TENANT_ROLE_HIRING_MANAGER = "hiring_manager"

WRITE_ROLES = {TENANT_ROLE_ADMIN, TENANT_ROLE_RECRUITER}
ALL_ROLES = {TENANT_ROLE_ADMIN, TENANT_ROLE_RECRUITER, TENANT_ROLE_VIEWER, TENANT_ROLE_HIRING_MANAGER}


def get_tenant_role(user: User) -> str:
    """Normalized tenant role; unknown values default to recruiter."""
    role = (getattr(user, "role", None) or TENANT_ROLE_RECRUITER).strip().lower()
    if role not in ALL_ROLES:
        return TENANT_ROLE_RECRUITER
    return role


def can_write_tenant(user: User) -> bool:
    return get_tenant_role(user) in WRITE_ROLES


def is_tenant_admin(user: User) -> bool:
    return get_tenant_role(user) == TENANT_ROLE_ADMIN


def is_tenant_viewer(user: User) -> bool:
    return get_tenant_role(user) == TENANT_ROLE_VIEWER


def is_hiring_manager(user: User) -> bool:
    return get_tenant_role(user) == TENANT_ROLE_HIRING_MANAGER


def can_read_tenant(user: User) -> bool:
    return get_tenant_role(user) in ALL_ROLES


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


def can_manage_requisition(user: User, req: Requisition) -> bool:
    if is_tenant_admin(user):
        return True
    if is_hiring_manager(user):
        return False
    if not can_write_tenant(user):
        return False
    owner_id = getattr(req, "created_by", None)
    return owner_id is None or owner_id == user.id


def require_requisition_access(user: User, req: Requisition, db: Session) -> None:
    """Read access — tenant members + assigned HMs."""
    from app.backend.services.requisition_service import hm_assigned_to_requisition

    if req.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Requisition not found")
    role = get_tenant_role(user)
    if role in {TENANT_ROLE_ADMIN, TENANT_ROLE_RECRUITER, TENANT_ROLE_VIEWER}:
        return
    if role == TENANT_ROLE_HIRING_MANAGER and hm_assigned_to_requisition(db, user.id, req.id):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"message": "You do not have access to this requisition.", "error_code": "REQ_ACCESS_FORBIDDEN"},
    )


def require_requisition_write(user: User, req: Requisition, db: Session) -> None:
    """Write access — recruiters/admins with ownership; HMs can edit intake when assigned."""
    from app.backend.services.requisition_service import hm_assigned_to_requisition

    if req.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Requisition not found")
    if is_tenant_admin(user):
        return
    if can_write_tenant(user) and can_manage_requisition(user, req):
        return
    if is_hiring_manager(user) and hm_assigned_to_requisition(db, user.id, req.id):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"message": "You cannot edit this requisition.", "error_code": "REQ_WRITE_FORBIDDEN"},
    )
