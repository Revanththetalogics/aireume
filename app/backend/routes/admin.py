"""
Platform admin routes — tenant management, audit logs, usage oversight.
All endpoints require platform admin privileges.
"""
import json
import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.backend.db.database import get_db
from app.backend.middleware.auth import (
    require_platform_admin,
    require_super_admin,
    require_support,
    require_security_admin,
    require_billing_admin,
    require_readonly_platform,
)
from app.backend.models.db_models import (
    AuditLog, Tenant, User, SubscriptionPlan, UsageLog,
    FeatureFlag, TenantFeatureOverride,
    Webhook, WebhookDelivery,
    PlatformConfig, TenantEmailConfig,
    SecurityEvent, ImpersonationSession, ErasureLog,
    PlanFeature, RateLimitConfig,
)
from app.backend.services.audit_service import log_audit
from app.backend.services.impersonation_service import (
    create_impersonation_session,
    list_active_sessions,
    revoke_impersonation_session_by_id,
)
from app.backend.services.security_event_service import get_security_events

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ─── Pydantic Models ────────────────────────────────────────────────────────────

class SuspendRequest(BaseModel):
    reason: str


class ChangePlanRequest(BaseModel):
    plan_id: int


class AdjustUsageRequest(BaseModel):
    analyses_count: Optional[int] = None
    storage_used_bytes: Optional[int] = None


class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    contact_email: Optional[str] = None
    plan_id: Optional[int] = None


class UpdateTenantRequest(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    contact_email: Optional[str] = None
    subscription_status: Optional[str] = None


class AddUserToTenantRequest(BaseModel):
    email: str
    role: str = "user"
    is_platform_admin: bool = False
    platform_role: Optional[str] = None


class TenantListItem(BaseModel):
    id: int
    name: str
    slug: str
    plan_name: Optional[str] = None
    plan_display_name: Optional[str] = None
    subscription_status: str
    analyses_count_this_month: int
    storage_used_bytes: int
    user_count: int
    created_at: Optional[str] = None
    suspended_at: Optional[str] = None


class TenantListResponse(BaseModel):
    items: list[TenantListItem]
    total: int
    page: int
    per_page: int
    pages: int


class TenantUserItem(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: Optional[str] = None


class UsageLogItem(BaseModel):
    id: int
    action: str
    quantity: int
    details: Optional[dict] = None
    created_at: Optional[str] = None
    user_email: Optional[str] = None


class AuditLogItem(BaseModel):
    id: int
    actor_email: str
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: Optional[str] = None


class AuditLogResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    per_page: int
    pages: int


class TenantDetailResponse(BaseModel):
    id: int
    name: str
    slug: str
    subscription_status: str
    plan_id: Optional[int] = None
    plan_name: Optional[str] = None
    plan_display_name: Optional[str] = None
    analyses_count_this_month: int
    storage_used_bytes: int
    suspended_at: Optional[str] = None
    suspended_reason: Optional[str] = None
    created_at: Optional[str] = None
    users: list[TenantUserItem]
    recent_usage_logs: list[UsageLogItem]
    recent_audit_logs: list[AuditLogItem]


# ─── Helpers ────────────────────────────────────────────────────────────────────

def _dt_to_iso(dt_value):
    """Safely convert a datetime to ISO string."""
    if dt_value is None:
        return None
    return dt_value.isoformat()


def _parse_audit_details(details_str):
    """Parse JSON details string from AuditLog."""
    if details_str is None:
        return None
    try:
        return json.loads(details_str)
    except (json.JSONDecodeError, TypeError):
        return None


# ─── 1. List Tenants ────────────────────────────────────────────────────────────

@router.get("/tenants", response_model=TenantListResponse)
def list_tenants(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    plan_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """List all tenants with pagination, search, and filters."""
    query = db.query(Tenant).options(joinedload(Tenant.plan))

    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Tenant.name.ilike(search_term)) | (Tenant.slug.ilike(search_term))
        )

    # Plan filter
    if plan_id is not None:
        query = query.filter(Tenant.plan_id == plan_id)

    # Status filter
    if status:
        query = query.filter(Tenant.subscription_status == status)

    # Total count before pagination
    total = query.count()

    # Sorting
    sort_column = getattr(Tenant, sort_by, Tenant.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Pagination
    offset = (page - 1) * per_page
    tenants = query.offset(offset).limit(per_page).all()

    pages = math.ceil(total / per_page) if total > 0 else 0

    items = []
    for t in tenants:
        user_count = db.query(func.count(User.id)).filter(User.tenant_id == t.id).scalar() or 0
        items.append(TenantListItem(
            id=t.id,
            name=t.name,
            slug=t.slug,
            plan_name=t.plan.name if t.plan else None,
            plan_display_name=t.plan.display_name if t.plan else None,
            subscription_status=t.subscription_status,
            analyses_count_this_month=t.analyses_count_this_month,
            storage_used_bytes=t.storage_used_bytes,
            user_count=user_count,
            created_at=_dt_to_iso(t.created_at),
            suspended_at=_dt_to_iso(t.suspended_at),
        ))

    return TenantListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


# ─── 2. Tenant Detail ──────────────────────────────────────────────────────────

@router.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
def get_tenant_detail(
    tenant_id: int,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Get full tenant detail with users, usage logs, and audit logs."""
    tenant = db.query(Tenant).options(joinedload(Tenant.plan)).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Users
    users = db.query(User).filter(User.tenant_id == tenant_id).all()
    user_items = [
        TenantUserItem(
            id=u.id,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            created_at=_dt_to_iso(u.created_at),
        )
        for u in users
    ]

    # Recent usage logs (last 20)
    usage_logs = (
        db.query(UsageLog)
        .filter(UsageLog.tenant_id == tenant_id)
        .order_by(UsageLog.created_at.desc())
        .limit(20)
        .all()
    )
    usage_items = [
        UsageLogItem(
            id=ul.id,
            action=ul.action,
            quantity=ul.quantity,
            details=_parse_audit_details(ul.details),
            created_at=_dt_to_iso(ul.created_at),
            user_email=ul.user.email if ul.user else None,
        )
        for ul in usage_logs
    ]

    # Recent audit logs for this tenant (last 20)
    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.resource_type == "tenant", AuditLog.resource_id == tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )
    audit_items = [
        AuditLogItem(
            id=al.id,
            actor_email=al.actor_email,
            action=al.action,
            resource_type=al.resource_type,
            resource_id=al.resource_id,
            details=_parse_audit_details(al.details),
            ip_address=al.ip_address,
            created_at=_dt_to_iso(al.created_at),
        )
        for al in audit_logs
    ]

    return TenantDetailResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        subscription_status=tenant.subscription_status,
        plan_id=tenant.plan_id,
        plan_name=tenant.plan.name if tenant.plan else None,
        plan_display_name=tenant.plan.display_name if tenant.plan else None,
        analyses_count_this_month=tenant.analyses_count_this_month,
        storage_used_bytes=tenant.storage_used_bytes,
        suspended_at=_dt_to_iso(tenant.suspended_at),
        suspended_reason=tenant.suspended_reason,
        created_at=_dt_to_iso(tenant.created_at),
        users=user_items,
        recent_usage_logs=usage_items,
        recent_audit_logs=audit_items,
    )


# ─── 3. Suspend Tenant ─────────────────────────────────────────────────────────

@router.post("/tenants/{tenant_id}/suspend")
def suspend_tenant(
    tenant_id: int,
    body: SuspendRequest,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Suspend a tenant account."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if tenant.suspended_at is not None:
        raise HTTPException(status_code=400, detail="Tenant is already suspended")

    tenant.suspended_at = datetime.now(timezone.utc)
    tenant.suspended_reason = body.reason
    tenant.subscription_status = "suspended"
    db.commit()

    log_audit(
        db,
        actor=admin,
        action="tenant.suspend",
        resource_type="tenant",
        resource_id=tenant_id,
        details={"reason": body.reason},
    )

    return {"message": "Tenant suspended", "tenant_id": tenant_id}


# ─── 4. Reactivate Tenant ──────────────────────────────────────────────────────

@router.post("/tenants/{tenant_id}/reactivate")
def reactivate_tenant(
    tenant_id: int,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Reactivate a suspended tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if tenant.suspended_at is None:
        raise HTTPException(status_code=400, detail="Tenant is not suspended")

    tenant.suspended_at = None
    tenant.suspended_reason = None
    tenant.subscription_status = "active"
    db.commit()

    log_audit(
        db,
        actor=admin,
        action="tenant.reactivate",
        resource_type="tenant",
        resource_id=tenant_id,
    )

    return {"message": "Tenant reactivated", "tenant_id": tenant_id}


# ─── 5. Change Plan ─────────────────────────────────────────────────────────────

@router.post("/tenants/{tenant_id}/change-plan")
def change_tenant_plan(
    tenant_id: int,
    body: ChangePlanRequest,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Change a tenant's subscription plan."""
    tenant = db.query(Tenant).options(joinedload(Tenant.plan)).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    new_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == body.plan_id).first()
    if not new_plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    old_plan_name = tenant.plan.name if tenant.plan else "none"
    old_plan_display = tenant.plan.display_name if tenant.plan else "None"
    old_plan_id = tenant.plan_id

    tenant.plan_id = body.plan_id
    db.commit()

    log_audit(
        db,
        actor=admin,
        action="tenant.change_plan",
        resource_type="tenant",
        resource_id=tenant_id,
        details={
            "old_plan_id": old_plan_id,
            "old_plan_name": old_plan_name,
            "old_plan_display_name": old_plan_display,
            "new_plan_id": new_plan.id,
            "new_plan_name": new_plan.name,
            "new_plan_display_name": new_plan.display_name,
        },
    )

    return {
        "message": "Plan changed successfully",
        "tenant_id": tenant_id,
        "old_plan": old_plan_name,
        "new_plan": new_plan.name,
    }


# ─── 6. Adjust Usage ────────────────────────────────────────────────────────────

@router.post("/tenants/{tenant_id}/adjust-usage")
def adjust_tenant_usage(
    tenant_id: int,
    body: AdjustUsageRequest,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Override usage counters for a tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    details = {}
    if body.analyses_count is not None:
        details["old_analyses_count"] = tenant.analyses_count_this_month
        details["new_analyses_count"] = body.analyses_count
        tenant.analyses_count_this_month = body.analyses_count

    if body.storage_used_bytes is not None:
        details["old_storage_used_bytes"] = tenant.storage_used_bytes
        details["new_storage_used_bytes"] = body.storage_used_bytes
        tenant.storage_used_bytes = body.storage_used_bytes

    db.commit()

    log_audit(
        db,
        actor=admin,
        action="tenant.adjust_usage",
        resource_type="tenant",
        resource_id=tenant_id,
        details=details,
    )

    return {
        "message": "Usage adjusted",
        "tenant_id": tenant_id,
        "analyses_count_this_month": tenant.analyses_count_this_month,
        "storage_used_bytes": tenant.storage_used_bytes,
    }


# ─── 7. Tenant Usage History ────────────────────────────────────────────────────

@router.get("/tenants/{tenant_id}/usage-history")
def get_tenant_usage_history(
    tenant_id: int,
    limit: int = Query(100, ge=1, le=500),
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Get usage logs for a specific tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    logs = (
        db.query(UsageLog)
        .filter(UsageLog.tenant_id == tenant_id)
        .order_by(UsageLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": ul.id,
            "action": ul.action,
            "quantity": ul.quantity,
            "details": _parse_audit_details(ul.details),
            "created_at": _dt_to_iso(ul.created_at),
            "user_email": ul.user.email if ul.user else None,
        }
        for ul in logs
    ]


# ─── Tenant CRUD Operations ─────────────────────────────────────────────

@router.post("/tenants")
def create_tenant(
    body: CreateTenantRequest,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Create a new tenant organization."""
    # Validate slug uniqueness
    existing = db.query(Tenant).filter(Tenant.slug == body.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Tenant slug '{body.slug}' already exists")

    # Validate plan if provided
    if body.plan_id:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == body.plan_id).first()
        if not plan:
            raise HTTPException(status_code=400, detail=f"Plan {body.plan_id} not found")

    tenant = Tenant(
        name=body.name,
        slug=body.slug,
        contact_email=body.contact_email,
        plan_id=body.plan_id,
        subscription_status="active",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # Create default rate limit config
    default_rate_limit = RateLimitConfig(
        tenant_id=tenant.id,
        requests_per_minute=60,
        llm_concurrent_max=2,
    )
    db.add(default_rate_limit)
    db.commit()

    log_audit(
        db, actor=admin, action="tenant.create",
        resource_type="tenant", resource_id=tenant.id,
        details={"name": tenant.name, "slug": tenant.slug},
    )

    return {
        "message": "Tenant created successfully",
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
    }


@router.put("/tenants/{tenant_id}")
def update_tenant(
    tenant_id: int,
    body: UpdateTenantRequest,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Update tenant details."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate slug uniqueness if changing
    if body.slug and body.slug != tenant.slug:
        existing = db.query(Tenant).filter(Tenant.slug == body.slug).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Tenant slug '{body.slug}' already exists")

    # Update fields
    updates = {}
    if body.name is not None:
        tenant.name = body.name
        updates["name"] = body.name
    if body.slug is not None:
        tenant.slug = body.slug
        updates["slug"] = body.slug
    if body.contact_email is not None:
        tenant.contact_email = body.contact_email
        updates["contact_email"] = body.contact_email
    if body.subscription_status is not None:
        tenant.subscription_status = body.subscription_status
        updates["subscription_status"] = body.subscription_status

    db.commit()
    db.refresh(tenant)

    log_audit(
        db, actor=admin, action="tenant.update",
        resource_type="tenant", resource_id=tenant_id,
        details=updates,
    )

    return {
        "message": "Tenant updated successfully",
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
    }


@router.delete("/tenants/{tenant_id}")
def delete_tenant(
    tenant_id: int,
    confirm: bool = Query(False),
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Delete a tenant and all associated data. Requires explicit confirmation."""
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required. Set confirm=true.")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant_name = tenant.name
    tenant_slug = tenant.slug

    # Delete tenant (cascade will remove associated data)
    db.delete(tenant)
    db.commit()

    log_audit(
        db, actor=admin, action="tenant.delete",
        resource_type="tenant", resource_id=tenant_id,
        details={"name": tenant_name, "slug": tenant_slug},
    )

    return {"message": f"Tenant '{tenant_name}' deleted successfully"}


# ─── Tenant User Management ─────────────────────────────────────────────

@router.post("/tenants/{tenant_id}/users")
def add_user_to_tenant(
    tenant_id: int,
    body: AddUserToTenantRequest,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Add an existing user to a tenant or create a new user account."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == body.email).first()
    if existing_user:
        # Update tenant assignment
        old_tenant_id = existing_user.tenant_id
        existing_user.tenant_id = tenant_id
        existing_user.role = body.role
        if body.is_platform_admin:
            existing_user.is_platform_admin = True
            existing_user.platform_role = body.platform_role or "support"
        db.commit()

        log_audit(
            db, actor=admin, action="user.update_tenant",
            resource_type="user", resource_id=existing_user.id,
            details={
                "email": body.email,
                "old_tenant_id": old_tenant_id,
                "new_tenant_id": tenant_id,
                "role": body.role,
            },
        )

        return {
            "message": "User tenant assignment updated",
            "user_id": existing_user.id,
            "email": existing_user.email,
        }

    # Create new user with temporary password
    import secrets
    from app.backend.services.auth_service import get_password_hash

    temp_password = secrets.token_urlsafe(12)
    hashed_pw = get_password_hash(temp_password)

    new_user = User(
        email=body.email,
        password_hash=hashed_pw,
        tenant_id=tenant_id,
        role=body.role,
        is_active=True,
        is_platform_admin=body.is_platform_admin,
        platform_role=body.platform_role if body.is_platform_admin else None,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit(
        db, actor=admin, action="user.create",
        resource_type="user", resource_id=new_user.id,
        details={
            "email": body.email,
            "tenant_id": tenant_id,
            "role": body.role,
        },
    )

    return {
        "message": "User created and added to tenant",
        "user_id": new_user.id,
        "email": new_user.email,
        "temporary_password": temp_password,
        "note": "User must change password on first login",
    }


@router.delete("/tenants/{tenant_id}/users/{user_id}")
def remove_user_from_tenant(
    tenant_id: int,
    user_id: int,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Remove a user from a tenant (soft delete by deactivating)."""
    user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in this tenant")

    # Deactivate user instead of deleting
    user.is_active = False
    db.commit()

    log_audit(
        db, actor=admin, action="user.deactivate",
        resource_type="user", resource_id=user_id,
        details={"email": user.email, "tenant_id": tenant_id},
    )

    return {"message": f"User '{user.email}' deactivated"}


# ─── 8. Audit Logs ──────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=AuditLogResponse)
def get_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    actor_email: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Query audit logs with filters and pagination."""
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if actor_email:
        query = query.filter(AuditLog.actor_email.ilike(f"%{actor_email}%"))
    if date_from:
        try:
            from_dt = datetime.fromisoformat(date_from)
            query = query.filter(AuditLog.created_at >= from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO 8601.")
    if date_to:
        try:
            to_dt = datetime.fromisoformat(date_to)
            query = query.filter(AuditLog.created_at <= to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO 8601.")

    total = query.count()

    logs = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    pages = math.ceil(total / per_page) if total > 0 else 0

    items = [
        AuditLogItem(
            id=al.id,
            actor_email=al.actor_email,
            action=al.action,
            resource_type=al.resource_type,
            resource_id=al.resource_id,
            details=_parse_audit_details(al.details),
            ip_address=al.ip_address,
            created_at=_dt_to_iso(al.created_at),
        )
        for al in logs
    ]

    return AuditLogResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


# ─── Feature Flags ─────────────────────────────────────
@router.get("/feature-flags")
def list_feature_flags(
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """List all feature flags with their global state."""
    flags = db.query(FeatureFlag).order_by(FeatureFlag.key).all()
    return [
        {
            "id": f.id,
            "key": f.key,
            "display_name": f.display_name,
            "description": f.description,
            "enabled_globally": f.enabled_globally,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in flags
    ]

@router.put("/feature-flags/{flag_id}")
def toggle_feature_flag(
    flag_id: int,
    body: dict,  # { "enabled_globally": bool }
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Toggle a feature flag's global state."""
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    
    old_state = flag.enabled_globally
    flag.enabled_globally = body.get("enabled_globally", flag.enabled_globally)
    db.commit()
    
    # Invalidate cache
    from app.backend.services.feature_flag_service import invalidate_cache
    invalidate_cache(feature_key=flag.key)
    
    log_audit(db, actor=admin, action="feature_flag.toggle", resource_type="feature_flag",
              resource_id=flag_id, details={"key": flag.key, "old": old_state, "new": flag.enabled_globally})
    
    return {"message": "Feature flag updated", "key": flag.key, "enabled_globally": flag.enabled_globally}

@router.get("/tenants/{tenant_id}/features")
def get_tenant_feature_overrides(
    tenant_id: int,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Get feature overrides for a specific tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    overrides = (
        db.query(TenantFeatureOverride)
        .filter(TenantFeatureOverride.tenant_id == tenant_id)
        .all()
    )
    return [
        {
            "id": o.id,
            "feature_flag_id": o.feature_flag_id,
            "feature_key": o.feature_flag.key if o.feature_flag else None,
            "enabled": o.enabled,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in overrides
    ]

@router.put("/tenants/{tenant_id}/features/{flag_id}")
def set_tenant_feature_override(
    tenant_id: int,
    flag_id: int,
    body: dict,  # { "enabled": bool }
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Set a feature override for a specific tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    
    override = (
        db.query(TenantFeatureOverride)
        .filter(TenantFeatureOverride.tenant_id == tenant_id, TenantFeatureOverride.feature_flag_id == flag_id)
        .first()
    )
    if override:
        override.enabled = body.get("enabled", override.enabled)
    else:
        override = TenantFeatureOverride(tenant_id=tenant_id, feature_flag_id=flag_id, enabled=body.get("enabled", True))
        db.add(override)
    db.commit()
    
    from app.backend.services.feature_flag_service import invalidate_cache
    invalidate_cache(tenant_id=tenant_id, feature_key=flag.key)
    
    log_audit(db, actor=admin, action="tenant_feature.override", resource_type="tenant",
              resource_id=tenant_id, details={"flag": flag.key, "enabled": override.enabled})
    
    return {"message": "Feature override set", "flag": flag.key, "enabled": override.enabled}

@router.delete("/tenants/{tenant_id}/features/{flag_id}")
def delete_tenant_feature_override(
    tenant_id: int,
    flag_id: int,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Remove a tenant feature override (revert to global)."""
    override = (
        db.query(TenantFeatureOverride)
        .filter(TenantFeatureOverride.tenant_id == tenant_id, TenantFeatureOverride.feature_flag_id == flag_id)
        .first()
    )
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")
    
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    db.delete(override)
    db.commit()
    
    from app.backend.services.feature_flag_service import invalidate_cache
    invalidate_cache(tenant_id=tenant_id)
    
    log_audit(db, actor=admin, action="tenant_feature.override_removed", resource_type="tenant",
              resource_id=tenant_id, details={"flag": flag.key if flag else str(flag_id)})
    
    return {"message": "Override removed, reverted to global setting"}


# ─── Platform Metrics ─────────────────────────────────────────────────────────

@router.get("/metrics/overview")
def get_platform_metrics_overview(
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Get platform-wide metrics overview."""
    from sqlalchemy import func as sa_func, case
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    # Tenant counts by status
    tenant_stats = db.query(
        Tenant.subscription_status,
        sa_func.count(Tenant.id)
    ).group_by(Tenant.subscription_status).all()

    tenant_counts = {"total": 0, "active": 0, "suspended": 0, "trialing": 0, "cancelled": 0, "past_due": 0}
    for status, count in tenant_stats:
        tenant_counts[status] = count
        tenant_counts["total"] += count

    # Also count suspended by suspended_at (since subscription_status might be "suspended")
    suspended_count = db.query(sa_func.count(Tenant.id)).filter(Tenant.suspended_at.isnot(None)).scalar()
    tenant_counts["suspended"] = suspended_count

    # User counts
    total_users = db.query(sa_func.count(User.id)).filter(User.is_active == True).scalar()

    # Analysis counts (from usage_logs)
    analyses_today = db.query(sa_func.coalesce(sa_func.sum(UsageLog.quantity), 0)).filter(
        UsageLog.action.in_(["resume_analysis", "batch_analysis"]),
        UsageLog.created_at >= today_start
    ).scalar()

    analyses_this_week = db.query(sa_func.coalesce(sa_func.sum(UsageLog.quantity), 0)).filter(
        UsageLog.action.in_(["resume_analysis", "batch_analysis"]),
        UsageLog.created_at >= week_start
    ).scalar()

    analyses_this_month = db.query(sa_func.coalesce(sa_func.sum(UsageLog.quantity), 0)).filter(
        UsageLog.action.in_(["resume_analysis", "batch_analysis"]),
        UsageLog.created_at >= month_start
    ).scalar()

    # Storage
    total_storage = db.query(sa_func.coalesce(sa_func.sum(Tenant.storage_used_bytes), 0)).scalar()

    # Plan distribution
    plan_dist = db.query(
        SubscriptionPlan.name,
        sa_func.count(Tenant.id)
    ).outerjoin(Tenant, Tenant.plan_id == SubscriptionPlan.id).group_by(SubscriptionPlan.name).all()
    plan_distribution = {name: count for name, count in plan_dist}

    # Revenue estimate (MRR = sum of monthly prices for active tenants)
    mrr_result = db.query(sa_func.coalesce(sa_func.sum(SubscriptionPlan.price_monthly), 0)).join(
        Tenant, Tenant.plan_id == SubscriptionPlan.id
    ).filter(Tenant.subscription_status == "active").scalar()

    return {
        "tenants": tenant_counts,
        "users": {"total": total_users},
        "analyses": {
            "today": int(analyses_today),
            "this_week": int(analyses_this_week),
            "this_month": int(analyses_this_month),
        },
        "storage": {"total_gb": round(total_storage / (1024 ** 3), 2)},
        "plans": plan_distribution,
        "revenue": {
            "mrr_cents": int(mrr_result),
            "arr_estimate_cents": int(mrr_result) * 12,
        },
    }


@router.get("/metrics/usage-trends")
def get_usage_trends(
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
    days: int = 30,
):
    """Get daily usage trends for the last N days."""
    from sqlalchemy import func as sa_func, cast, Date
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    # Daily analysis counts
    daily_analyses = db.query(
        sa_func.date(UsageLog.created_at).label("day"),
        sa_func.coalesce(sa_func.sum(UsageLog.quantity), 0).label("count")
    ).filter(
        UsageLog.action.in_(["resume_analysis", "batch_analysis"]),
        UsageLog.created_at >= start_date
    ).group_by(sa_func.date(UsageLog.created_at)).order_by(sa_func.date(UsageLog.created_at)).all()

    # Daily new tenant signups
    daily_signups = db.query(
        sa_func.date(Tenant.created_at).label("day"),
        sa_func.count(Tenant.id).label("count")
    ).filter(
        Tenant.created_at >= start_date
    ).group_by(sa_func.date(Tenant.created_at)).order_by(sa_func.date(Tenant.created_at)).all()

    return {
        "period_days": days,
        "analyses": [{"date": str(day), "count": int(count)} for day, count in daily_analyses],
        "signups": [{"date": str(day), "count": int(count)} for day, count in daily_signups],
    }


# ─── Webhooks ─────────────────────────────────────

@router.get("/tenants/{tenant_id}/webhooks")
def list_tenant_webhooks(
    tenant_id: int,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """List all webhooks for a tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    webhooks = db.query(Webhook).filter(Webhook.tenant_id == tenant_id).all()
    return [
        {
            "id": w.id,
            "url": w.url,
            "events": json.loads(w.events) if w.events else [],
            "is_active": w.is_active,
            "failure_count": w.failure_count,
            "last_triggered_at": w.last_triggered_at.isoformat() if w.last_triggered_at else None,
            "last_failure_at": w.last_failure_at.isoformat() if w.last_failure_at else None,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in webhooks
    ]


@router.post("/tenants/{tenant_id}/webhooks")
def create_tenant_webhook(
    tenant_id: int,
    body: dict,  # { "url": str, "secret": str, "events": list[str] }
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Create a new webhook for a tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    import secrets as secrets_mod
    webhook = Webhook(
        tenant_id=tenant_id,
        url=body.get("url", ""),
        secret=body.get("secret", secrets_mod.token_hex(32)),
        events=json.dumps(body.get("events", ["*"])),
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    log_audit(db, actor=admin, action="webhook.create", resource_type="webhook",
              resource_id=webhook.id, details={"tenant_id": tenant_id, "url": webhook.url})

    return {"id": webhook.id, "url": webhook.url, "secret": webhook.secret, "events": body.get("events", ["*"])}


@router.delete("/tenants/{tenant_id}/webhooks/{webhook_id}")
def delete_tenant_webhook(
    tenant_id: int,
    webhook_id: int,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Delete a webhook."""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.tenant_id == tenant_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    db.delete(webhook)
    db.commit()

    log_audit(db, actor=admin, action="webhook.delete", resource_type="webhook",
              resource_id=webhook_id, details={"tenant_id": tenant_id})

    return {"message": "Webhook deleted"}


@router.get("/tenants/{tenant_id}/webhooks/{webhook_id}/deliveries")
def list_webhook_deliveries(
    tenant_id: int,
    webhook_id: int,
    limit: int = 50,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """List delivery history for a webhook."""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.tenant_id == tenant_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    deliveries = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": d.id,
            "event": d.event,
            "response_status": d.response_status,
            "success": d.success,
            "attempt": d.attempt,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in deliveries
    ]


# ─── Billing Configuration ────────────────────────────────────────────────────

def _mask_sensitive(value: str) -> str:
    """Mask a sensitive value, showing only the last 4 characters."""
    if not value or len(value) <= 4:
        return "****"
    return "*" * (len(value) - 4) + value[-4:]


_SENSITIVE_KEY_PATTERNS = ("api_key", "key_secret", "webhook_secret")


def _is_sensitive_key(key: str) -> bool:
    """Check if a config key holds a sensitive value that should be masked."""
    return any(p in key for p in _SENSITIVE_KEY_PATTERNS)


@router.get("/billing/config")
def get_billing_config(
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Get current billing provider configuration (sensitive values masked)."""
    configs = db.query(PlatformConfig).filter(
        PlatformConfig.config_key.startswith("billing.")
    ).all()

    active_provider = "manual"
    config_items = []
    for c in configs:
        if c.config_key == "billing.active_provider":
            active_provider = c.config_value
            config_items.append({
                "key": c.config_key,
                "value": c.config_value,
                "description": c.description,
            })
        else:
            value = _mask_sensitive(c.config_value) if _is_sensitive_key(c.config_key) else c.config_value
            config_items.append({
                "key": c.config_key,
                "value": value,
                "description": c.description,
            })

    return {
        "active_provider": active_provider,
        "configs": config_items,
    }


@router.put("/billing/config")
def set_billing_config(
    body: dict,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Set active billing provider and credentials.

    Expected body::

        {
            "active_provider": "stripe" | "razorpay" | "manual",
            "configs": {
                "billing.stripe.api_key": "sk_test_...",
                "billing.stripe.webhook_secret": "whsec_...",
                ...
            }
        }
    """
    active_provider = body.get("active_provider", "manual")
    configs = body.get("configs", {})

    # Validate provider name
    from app.backend.services.billing.factory import PROVIDER_REGISTRY
    if active_provider not in PROVIDER_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {active_provider}")

    # Upsert active_provider config
    existing = db.query(PlatformConfig).filter(
        PlatformConfig.config_key == "billing.active_provider"
    ).first()
    if existing:
        existing.config_value = active_provider
        existing.updated_by = admin.id
        existing.updated_at = datetime.now(timezone.utc)
    else:
        db.add(PlatformConfig(
            config_key="billing.active_provider",
            config_value=active_provider,
            description="Active payment provider",
            updated_by=admin.id,
            updated_at=datetime.now(timezone.utc),
        ))

    # Upsert provider-specific configs
    for key, value in configs.items():
        if not key.startswith("billing."):
            continue
        existing = db.query(PlatformConfig).filter(
            PlatformConfig.config_key == key
        ).first()
        if existing:
            existing.config_value = value
            existing.updated_by = admin.id
            existing.updated_at = datetime.now(timezone.utc)
        else:
            db.add(PlatformConfig(
                config_key=key,
                config_value=value,
                updated_by=admin.id,
                updated_at=datetime.now(timezone.utc),
            ))

    db.commit()

    log_audit(db, actor=admin, action="billing.config_updated", resource_type="platform_config",
              resource_id=None, details={"active_provider": active_provider})

    return {"message": "Billing configuration updated", "active_provider": active_provider}


@router.get("/billing/providers")
def list_billing_providers(
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """List available billing providers with their required config fields."""
    from app.backend.services.billing.factory import PROVIDER_REGISTRY

    providers = []
    for name, entry in PROVIDER_REGISTRY.items():
        providers.append({
            "name": name,
            "required_config_keys": entry["config_keys"],
        })

    return providers


# ─── Email Notification Endpoints ─────────────────────────────────────────────

@router.get("/notifications/config")
def get_notification_config(
    admin: User = Depends(require_platform_admin),
):
    """Return SMTP configuration status (password never exposed)."""
    from app.backend.services.email_service import email_service

    return {
        "configured": email_service.is_configured,
        "smtp_host": email_service.smtp_host,
        "smtp_from": email_service.smtp_from,
    }


class TestEmailRequest(BaseModel):
    email: Optional[str] = None


@router.post("/notifications/test")
def send_test_email(
    body: TestEmailRequest = TestEmailRequest(),
    admin: User = Depends(require_platform_admin),
):
    """Send a test email to the requesting admin's address (or a provided one).

    Requires platform admin privileges.
    """
    from app.backend.services.email_service import email_service

    recipient = body.email or admin.email
    html = (
        "<h2>Test Email from ARIA</h2>"
        "<p>This is a test notification sent by the ARIA admin panel.</p>"
        "<p>If you received this, SMTP is correctly configured.</p>"
        "<hr><p style='color:gray;font-size:12px;'>"
        "Automated message from ARIA Resume Intelligence.</p>"
    )
    success = email_service.send_email(
        to=recipient,
        subject="ARIA — Test Notification",
        body_html=html,
    )

    if success:
        return {"message": "Test email sent", "recipient": recipient}
    if not email_service.is_configured:
        return {"message": "SMTP not configured — email not sent", "recipient": recipient}
    return {"message": "Failed to send test email", "recipient": recipient}


# --- Tenant Email Configuration ---------------------------------------------


class EmailConfigRequest(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: str
    smtp_from: str
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    encryption_type: str = "tls"  # tls | ssl | none


def _mask_smtp_password(pw: str) -> str:
    """Mask password showing only first and last char, or dots if too short."""
    if not pw:
        return ""
    if len(pw) <= 4:
        return "****"
    return pw[0] + "*" * (len(pw) - 2) + pw[-1]


@router.post("/email-config")
def upsert_email_config(
    body: EmailConfigRequest,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Create or update the tenant SMTP email configuration.

    Passwords are encrypted with Fernet before storage.
    """
    from app.backend.services.email_service import encrypt_password

    config = db.query(TenantEmailConfig).filter(
        TenantEmailConfig.tenant_id == admin.tenant_id
    ).first()

    encrypted_pw = encrypt_password(body.smtp_password)

    if config:
        config.smtp_host = body.smtp_host
        config.smtp_port = body.smtp_port
        config.smtp_user = body.smtp_user
        config.smtp_password = encrypted_pw
        config.smtp_from = body.smtp_from
        config.from_name = body.from_name
        config.reply_to = body.reply_to
        config.encryption_type = body.encryption_type
        config.is_active = True
        config.configured_by = admin.id
        config.updated_at = datetime.now(timezone.utc)
    else:
        config = TenantEmailConfig(
            tenant_id=admin.tenant_id,
            smtp_host=body.smtp_host,
            smtp_port=body.smtp_port,
            smtp_user=body.smtp_user,
            smtp_password=encrypted_pw,
            smtp_from=body.smtp_from,
            from_name=body.from_name,
            reply_to=body.reply_to,
            encryption_type=body.encryption_type,
            is_active=True,
            configured_by=admin.id,
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    log_audit(
        db, actor=admin, action="email_config.upsert",
        resource_type="tenant_email_config", resource_id=config.id,
        details={"smtp_host": body.smtp_host, "smtp_from": body.smtp_from},
    )

    return {
        "id": config.id,
        "smtp_host": config.smtp_host,
        "smtp_port": config.smtp_port,
        "smtp_user": config.smtp_user,
        "smtp_password": _mask_smtp_password(body.smtp_password),
        "smtp_from": config.smtp_from,
        "from_name": config.from_name,
        "reply_to": config.reply_to,
        "encryption_type": config.encryption_type,
        "is_active": config.is_active,
        "configured_by": config.configured_by,
        "last_test_at": _dt_to_iso(config.last_test_at),
        "last_test_success": config.last_test_success,
        "created_at": _dt_to_iso(config.created_at),
        "updated_at": _dt_to_iso(config.updated_at),
    }


@router.get("/email-config")
def get_email_config(
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Get the email configuration for the current admin's tenant.

    Password is masked in the response.
    """
    config = db.query(TenantEmailConfig).filter(
        TenantEmailConfig.tenant_id == admin.tenant_id
    ).first()

    if not config:
        return {"configured": False}

    return {
        "configured": True,
        "id": config.id,
        "smtp_host": config.smtp_host,
        "smtp_port": config.smtp_port,
        "smtp_user": config.smtp_user,
        "smtp_password": _mask_smtp_password(config.smtp_password),
        "smtp_from": config.smtp_from,
        "from_name": config.from_name,
        "reply_to": config.reply_to,
        "encryption_type": config.encryption_type,
        "is_active": config.is_active,
        "configured_by": config.configured_by,
        "last_test_at": _dt_to_iso(config.last_test_at),
        "last_test_success": config.last_test_success,
        "created_at": _dt_to_iso(config.created_at),
        "updated_at": _dt_to_iso(config.updated_at),
    }


@router.post("/email-config/test")
def test_email_config(
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Send a test email using the tenant's saved SMTP configuration.

    Updates last_test_at and last_test_success on the config record.
    """
    from app.backend.services.email_service import get_tenant_email_service

    config = db.query(TenantEmailConfig).filter(
        TenantEmailConfig.tenant_id == admin.tenant_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=404,
            detail="No email configuration found for this tenant. Create one first.",
        )

    tenant_service = get_tenant_email_service(db, admin.tenant_id)
    if not tenant_service:
        raise HTTPException(
            status_code=500,
            detail="Failed to load tenant email configuration. Check ENCRYPTION_KEY.",
        )

    recipient = admin.email
    html = (
        "<h2>Test Email from ARIA (Tenant SMTP)</h2>"
        "<p>This is a test email sent using your tenant's SMTP configuration.</p>"
        "<p>If you received this, your tenant email settings are working correctly.</p>"
        "<hr><p style='color:gray;font-size:12px'>"
        "Automated message from ARIA Resume Intelligence.</p>"
    )
    success = tenant_service.send_email(
        to=recipient,
        subject="ARIA - Tenant SMTP Test",
        body_html=html,
    )

    config.last_test_at = datetime.now(timezone.utc)
    config.last_test_success = success
    db.commit()

    if success:
        return {"message": "Test email sent successfully", "recipient": recipient}
    return {
        "message": "Failed to send test email - check your SMTP credentials",
        "recipient": recipient,
    }


@router.delete("/email-config")
def delete_email_config(
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Remove the tenant email configuration (revert to system default)."""
    config = db.query(TenantEmailConfig).filter(
        TenantEmailConfig.tenant_id == admin.tenant_id
    ).first()

    if not config:
        raise HTTPException(
            status_code=404,
            detail="No email configuration found for this tenant.",
        )

    log_audit(
        db, actor=admin, action="email_config.delete",
        resource_type="tenant_email_config", resource_id=config.id,
        details={"smtp_host": config.smtp_host, "smtp_from": config.smtp_from},
    )

    db.delete(config)
    db.commit()

    return {"message": "Email configuration removed - system default will be used"}


# ─── Security Events ───────────────────────────────────────────────────────────

class SecurityEventItem(BaseModel):
    id: int
    event_type: str
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[dict] = None
    created_at: Optional[str] = None


class SecurityEventResponse(BaseModel):
    items: list[SecurityEventItem]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("/security-events", response_model=SecurityEventResponse)
def get_security_events_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    event_type: Optional[str] = Query(None),
    tenant_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    ip_address: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    admin: User = Depends(require_security_admin),
    db: Session = Depends(get_db),
):
    """Query security events with filters and pagination."""
    from_dt = None
    to_dt = None
    if date_from:
        try:
            from_dt = datetime.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO 8601.")
    if date_to:
        try:
            to_dt = datetime.fromisoformat(date_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO 8601.")

    items, total = get_security_events(
        db,
        event_type=event_type,
        tenant_id=tenant_id,
        user_id=user_id,
        ip_address=ip_address,
        date_from=from_dt,
        date_to=to_dt,
        limit=per_page,
        offset=(page - 1) * per_page,
    )

    pages = math.ceil(total / per_page) if total > 0 else 0

    return SecurityEventResponse(
        items=[
            SecurityEventItem(
                id=e.id,
                event_type=e.event_type,
                tenant_id=e.tenant_id,
                user_id=e.user_id,
                ip_address=e.ip_address,
                user_agent=e.user_agent,
                details=_parse_audit_details(e.details),
                created_at=_dt_to_iso(e.created_at),
            )
            for e in items
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


# ─── Impersonation ─────────────────────────────────────────────────────────────

class ImpersonationSessionItem(BaseModel):
    id: int
    admin_user_id: int
    target_user_id: int
    target_email: Optional[str] = None
    admin_email: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: Optional[str] = None
    ip_address: Optional[str] = None


@router.post("/impersonate/{user_id}")
def impersonate_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_support),
    db: Session = Depends(get_db),
):
    """Create an impersonation session for a target user. Returns a one-time token."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    ip = request.client.host if request.client else ""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()

    raw_token = create_impersonation_session(
        db,
        admin_user_id=admin.id,
        target_user_id=target.id,
        ip_address=ip,
        ttl_minutes=15,
    )

    log_audit(
        db,
        actor=admin,
        action="impersonation.start",
        resource_type="user",
        resource_id=target.id,
        details={"target_email": target.email, "ip": ip},
    )

    from app.backend.services.security_event_service import record_impersonation
    record_impersonation(db, admin_id=admin.id, target_id=target.id, ip_address=ip, started=True)

    return {
        "message": "Impersonation session created",
        "impersonation_token": raw_token,
        "target_user": {"id": target.id, "email": target.email, "tenant_id": target.tenant_id},
        "expires_in_minutes": 15,
    }


@router.get("/impersonate/sessions")
def list_impersonation_sessions(
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """List all active impersonation sessions."""
    sessions = list_active_sessions(db)
    return [
        ImpersonationSessionItem(
            id=s.id,
            admin_user_id=s.admin_user_id,
            target_user_id=s.target_user_id,
            target_email=s.target_user.email if s.target_user else None,
            admin_email=s.admin_user.email if s.admin_user else None,
            expires_at=_dt_to_iso(s.expires_at),
            created_at=_dt_to_iso(s.created_at),
            ip_address=s.ip_address,
        )
        for s in sessions
    ]


@router.delete("/impersonate/sessions/{session_id}")
def revoke_impersonation(
    session_id: int,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Revoke an active impersonation session."""
    session = db.query(ImpersonationSession).filter(ImpersonationSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    success = revoke_impersonation_session_by_id(db, session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Session already revoked or expired")

    log_audit(
        db,
        actor=admin,
        action="impersonation.revoke",
        resource_type="impersonation_session",
        resource_id=session_id,
        details={"target_user_id": session.target_user_id},
    )

    return {"message": "Impersonation session revoked", "session_id": session_id}


# ─── GDPR Data Erasure ─────────────────────────────────────────────────────────

class ErasureRequest(BaseModel):
    confirm: bool


class ErasureLogItem(BaseModel):
    id: int
    tenant_id: int
    actor_email: Optional[str] = None
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    records_affected: int
    created_at: Optional[str] = None


@router.post("/tenants/{tenant_id}/anonymize")
def anonymize_tenant(
    tenant_id: int,
    body: ErasureRequest,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Request GDPR data erasure for a tenant. Requires explicit confirmation."""
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required. Set confirm=true.")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Auto-suspend if not already
    if tenant.suspended_at is None:
        tenant.suspended_at = datetime.now(timezone.utc)
        tenant.suspended_reason = "GDPR data erasure (preparation)"
        db.commit()

    from app.backend.services.erasure_service import request_erasure, execute_erasure

    log = request_erasure(db, tenant_id=tenant_id, actor_user_id=admin.id)

    # Execute immediately (can be made async in future)
    try:
        records_affected = execute_erasure(db, erasure_log_id=log.id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erasure failed: {str(exc)}")

    log_audit(
        db,
        actor=admin,
        action="tenant.anonymize",
        resource_type="tenant",
        resource_id=tenant_id,
        details={"erasure_log_id": log.id, "records_affected": records_affected},
    )

    return {
        "message": "Tenant data erasure completed",
        "tenant_id": tenant_id,
        "erasure_log_id": log.id,
        "records_affected": records_affected,
        "status": "completed",
    }


@router.get("/tenants/{tenant_id}/anonymize")
def list_erasure_logs(
    tenant_id: int,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """List erasure logs for a tenant."""
    logs = (
        db.query(ErasureLog)
        .filter(ErasureLog.tenant_id == tenant_id)
        .order_by(ErasureLog.created_at.desc())
        .all()
    )
    return [
        ErasureLogItem(
            id=log.id,
            tenant_id=log.tenant_id,
            actor_email=log.actor.email if log.actor else None,
            status=log.status,
            started_at=_dt_to_iso(log.started_at),
            completed_at=_dt_to_iso(log.completed_at),
            records_affected=log.records_affected,
            created_at=_dt_to_iso(log.created_at),
        )
        for log in logs
    ]


@router.get("/tenants/{tenant_id}/anonymize/{erasure_log_id}")
def get_erasure_detail(
    tenant_id: int,
    erasure_log_id: int,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Get details of a specific erasure request."""
    log = (
        db.query(ErasureLog)
        .filter(ErasureLog.id == erasure_log_id, ErasureLog.tenant_id == tenant_id)
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="Erasure log not found")

    return ErasureLogItem(
        id=log.id,
        tenant_id=log.tenant_id,
        actor_email=log.actor.email if log.actor else None,
        status=log.status,
        started_at=_dt_to_iso(log.started_at),
        completed_at=_dt_to_iso(log.completed_at),
        records_affected=log.records_affected,
        created_at=_dt_to_iso(log.created_at),
    )


# ─── Plan-Feature Entitlement Management ───────────────────────────────────────

class PlanFeatureItem(BaseModel):
    id: int
    plan_id: int
    feature_flag_id: int
    feature_key: Optional[str] = None
    feature_name: Optional[str] = None
    enabled: bool
    created_at: Optional[str] = None


@router.get("/plans/{plan_id}/features")
def get_plan_feature_mappings(
    plan_id: int,
    admin: User = Depends(require_billing_admin),
    db: Session = Depends(get_db),
):
    """List all feature flag mappings for a subscription plan."""
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    mappings = (
        db.query(PlanFeature)
        .filter(PlanFeature.plan_id == plan_id)
        .all()
    )
    return [
        PlanFeatureItem(
            id=m.id,
            plan_id=m.plan_id,
            feature_flag_id=m.feature_flag_id,
            feature_key=m.feature_flag.key if m.feature_flag else None,
            feature_name=m.feature_flag.display_name if m.feature_flag else None,
            enabled=m.enabled,
            created_at=_dt_to_iso(m.created_at),
        )
        for m in mappings
    ]


@router.put("/plans/{plan_id}/features/{feature_flag_id}")
def update_plan_feature_mapping(
    plan_id: int,
    feature_flag_id: int,
    body: dict,  # { "enabled": bool }
    admin: User = Depends(require_billing_admin),
    db: Session = Depends(get_db),
):
    """Enable or disable a feature for a specific subscription plan."""
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    flag = db.query(FeatureFlag).filter(FeatureFlag.id == feature_flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")

    mapping = (
        db.query(PlanFeature)
        .filter(PlanFeature.plan_id == plan_id, PlanFeature.feature_flag_id == feature_flag_id)
        .first()
    )

    enabled = body.get("enabled", True)
    if mapping:
        mapping.enabled = enabled
    else:
        mapping = PlanFeature(
            plan_id=plan_id,
            feature_flag_id=feature_flag_id,
            enabled=enabled,
        )
        db.add(mapping)

    db.commit()
    db.refresh(mapping)

    # Invalidate cache for all tenants on this plan
    from app.backend.services.feature_flag_service import invalidate_cache
    tenants = db.query(Tenant).filter(Tenant.plan_id == plan_id).all()
    for t in tenants:
        invalidate_cache(tenant_id=t.id, feature_key=flag.key)

    log_audit(
        db, actor=admin, action="plan_feature.update",
        resource_type="plan_feature", resource_id=mapping.id,
        details={"plan_id": plan_id, "feature_flag_id": feature_flag_id, "enabled": enabled},
    )

    return PlanFeatureItem(
        id=mapping.id,
        plan_id=mapping.plan_id,
        feature_flag_id=mapping.feature_flag_id,
        feature_key=flag.key,
        feature_name=flag.display_name,
        enabled=mapping.enabled,
        created_at=_dt_to_iso(mapping.created_at),
    )


@router.delete("/plans/{plan_id}/features/{feature_flag_id}")
def delete_plan_feature_mapping(
    plan_id: int,
    feature_flag_id: int,
    admin: User = Depends(require_billing_admin),
    db: Session = Depends(get_db),
):
    """Remove a plan-feature mapping (reverts to global flag default)."""
    mapping = (
        db.query(PlanFeature)
        .filter(PlanFeature.plan_id == plan_id, PlanFeature.feature_flag_id == feature_flag_id)
        .first()
    )
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    flag = db.query(FeatureFlag).filter(FeatureFlag.id == feature_flag_id).first()

    db.delete(mapping)
    db.commit()

    # Invalidate cache for all tenants on this plan
    from app.backend.services.feature_flag_service import invalidate_cache
    tenants = db.query(Tenant).filter(Tenant.plan_id == plan_id).all()
    for t in tenants:
        invalidate_cache(tenant_id=t.id, feature_key=flag.key if flag else None)

    log_audit(
        db, actor=admin, action="plan_feature.delete",
        resource_type="plan_feature", resource_id=None,
        details={"plan_id": plan_id, "feature_flag_id": feature_flag_id},
    )

    return {"message": "Plan-feature mapping removed", "plan_id": plan_id, "feature_flag_id": feature_flag_id}


# ─── Rate Limit Configuration ────────────────────────────────────────────────

class RateLimitConfigItem(BaseModel):
    id: int
    tenant_id: int
    tenant_name: Optional[str] = None
    tenant_slug: Optional[str] = None
    requests_per_minute: int
    llm_concurrent_max: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RateLimitConfigUpdate(BaseModel):
    requests_per_minute: Optional[int] = None
    llm_concurrent_max: Optional[int] = None


@router.get("/rate-limits")
def list_rate_limit_configs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """List all tenant rate limit configurations with pagination and search."""
    query = db.query(RateLimitConfig, Tenant).join(
        Tenant, RateLimitConfig.tenant_id == Tenant.id
    )

    if search:
        search_filter = f"%{search.lower()}%"
        query = query.filter(
            (Tenant.name.ilike(search_filter)) | (Tenant.slug.ilike(search_filter))
        )

    total = query.count()
    configs = query.order_by(Tenant.name).offset((page - 1) * per_page).limit(per_page).all()

    pages = math.ceil(total / per_page) if total > 0 else 0

    return {
        "items": [
            {
                "id": config.id,
                "tenant_id": config.tenant_id,
                "tenant_name": tenant.name,
                "tenant_slug": tenant.slug,
                "requests_per_minute": config.requests_per_minute,
                "llm_concurrent_max": config.llm_concurrent_max,
                "created_at": _dt_to_iso(config.created_at),
                "updated_at": _dt_to_iso(config.updated_at),
            }
            for config, tenant in configs
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


@router.get("/tenants/{tenant_id}/rate-limit")
def get_tenant_rate_limit(
    tenant_id: int,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Get rate limit configuration for a specific tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    config = db.query(RateLimitConfig).filter(
        RateLimitConfig.tenant_id == tenant_id
    ).first()

    if not config:
        return {
            "configured": False,
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "defaults": {
                "requests_per_minute": 60,
                "llm_concurrent_max": 2,
            }
        }

    return {
        "configured": True,
        "id": config.id,
        "tenant_id": config.tenant_id,
        "tenant_name": tenant.name,
        "tenant_slug": tenant.slug,
        "requests_per_minute": config.requests_per_minute,
        "llm_concurrent_max": config.llm_concurrent_max,
        "created_at": _dt_to_iso(config.created_at),
        "updated_at": _dt_to_iso(config.updated_at),
    }


@router.put("/tenants/{tenant_id}/rate-limit")
def update_tenant_rate_limit(
    tenant_id: int,
    body: RateLimitConfigUpdate,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Create or update rate limit configuration for a tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Validate inputs
    if body.requests_per_minute is not None and body.requests_per_minute < 1:
        raise HTTPException(status_code=400, detail="requests_per_minute must be >= 1")
    if body.llm_concurrent_max is not None and body.llm_concurrent_max < 1:
        raise HTTPException(status_code=400, detail="llm_concurrent_max must be >= 1")

    config = db.query(RateLimitConfig).filter(
        RateLimitConfig.tenant_id == tenant_id
    ).first()

    if config:
        # Update existing
        if body.requests_per_minute is not None:
            config.requests_per_minute = body.requests_per_minute
        if body.llm_concurrent_max is not None:
            config.llm_concurrent_max = body.llm_concurrent_max
        config.updated_at = datetime.now(timezone.utc)
    else:
        # Create new with defaults
        config = RateLimitConfig(
            tenant_id=tenant_id,
            requests_per_minute=body.requests_per_minute or 60,
            llm_concurrent_max=body.llm_concurrent_max or 2,
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    # Invalidate rate limit cache in middleware
    from app.backend.middleware.rate_limit import RateLimitMiddleware
    if RateLimitMiddleware._instance:
        RateLimitMiddleware._instance.config_cache.pop(tenant_id, None)

    log_audit(
        db, actor=admin, action="rate_limit.update",
        resource_type="rate_limit_config", resource_id=config.id,
        details={
            "tenant_id": tenant_id,
            "requests_per_minute": config.requests_per_minute,
            "llm_concurrent_max": config.llm_concurrent_max,
        },
    )

    return {
        "message": "Rate limit configuration updated",
        "id": config.id,
        "tenant_id": config.tenant_id,
        "requests_per_minute": config.requests_per_minute,
        "llm_concurrent_max": config.llm_concurrent_max,
        "updated_at": _dt_to_iso(config.updated_at),
    }


@router.delete("/tenants/{tenant_id}/rate-limit")
def delete_tenant_rate_limit(
    tenant_id: int,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Delete tenant rate limit configuration (revert to defaults)."""
    config = db.query(RateLimitConfig).filter(
        RateLimitConfig.tenant_id == tenant_id
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="Rate limit configuration not found")

    db.delete(config)
    db.commit()

    # Invalidate cache
    from app.backend.middleware.rate_limit import RateLimitMiddleware
    if RateLimitMiddleware._instance:
        RateLimitMiddleware._instance.config_cache.pop(tenant_id, None)

    log_audit(
        db, actor=admin, action="rate_limit.delete",
        resource_type="rate_limit_config", resource_id=config.id,
        details={"tenant_id": tenant_id},
    )

    return {"message": "Rate limit configuration deleted, tenant will use defaults"}
