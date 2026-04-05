"""
Subscription routes: current plan, usage tracking, available plans, subscription management.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user, require_admin
from app.backend.models.db_models import (
    Tenant, User, SubscriptionPlan, UsageLog, Candidate
)
from app.backend.models.schemas import SubscriptionResponse, PlanInfo, UsageStats

router = APIRouter(prefix="/api/subscription", tags=["subscription"])


# ─── Pydantic Models ────────────────────────────────────────────────────────────

class PlanResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: str
    price_monthly: int
    price_yearly: int
    currency: str
    features: list[str]
    limits: dict


class CurrentPlanResponse(BaseModel):
    plan: PlanResponse
    status: str
    billing_cycle: str
    current_period_start: Optional[str]
    current_period_end: Optional[str]
    price: int


class UsageResponse(BaseModel):
    analyses_used: int
    analyses_limit: int
    storage_used_mb: float
    storage_limit_gb: int
    team_members_count: int
    team_members_limit: int
    percent_used: float


class FullSubscriptionResponse(BaseModel):
    current_plan: CurrentPlanResponse
    usage: UsageResponse
    available_plans: list[PlanResponse]
    days_until_reset: int


class UsageCheckResponse(BaseModel):
    allowed: bool
    current_usage: int
    limit: int
    message: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ensure_monthly_reset(tenant: Tenant) -> None:
    """Reset monthly usage counters if it's a new month."""
    now = datetime.now(timezone.utc)
    
    if tenant.usage_reset_at is None:
        tenant.usage_reset_at = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return
    
    # Check if we're in a different month than the last reset
    if now.year != tenant.usage_reset_at.year or now.month != tenant.usage_reset_at.month:
        tenant.analyses_count_this_month = 0
        tenant.usage_reset_at = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _get_plan_limits(plan: SubscriptionPlan) -> dict:
    """Parse JSON limits from subscription plan."""
    try:
        return json.loads(plan.limits) if plan.limits else {}
    except json.JSONDecodeError:
        return {}


def _get_plan_features(plan: SubscriptionPlan) -> list[str]:
    """Parse JSON features from subscription plan."""
    try:
        return json.loads(plan.features) if plan.features else []
    except json.JSONDecodeError:
        return []


def _plan_to_response(plan: SubscriptionPlan) -> PlanResponse:
    """Convert a SubscriptionPlan model to API response."""
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        display_name=plan.display_name or plan.name.title(),
        description=plan.description or "",
        price_monthly=plan.price_monthly,
        price_yearly=plan.price_yearly,
        currency=plan.currency,
        features=_get_plan_features(plan),
        limits=_get_plan_limits(plan),
    )


def _calculate_storage_usage(db: Session, tenant_id: int) -> int:
    """Calculate actual storage used by tenant in bytes."""
    # Sum of resume file sizes (approximate via text length)
    total_bytes = db.query(func.sum(func.length(Candidate.raw_resume_text))).filter(
        Candidate.tenant_id == tenant_id
    ).scalar() or 0
    
    # Add parser snapshot sizes
    snapshot_bytes = db.query(func.sum(func.length(Candidate.parser_snapshot_json))).filter(
        Candidate.tenant_id == tenant_id
    ).scalar() or 0
    
    return int(total_bytes + snapshot_bytes)


def _calculate_days_until_reset(tenant: Tenant) -> int:
    """Calculate days until monthly usage reset."""
    now = datetime.now(timezone.utc)
    
    # Get next month
    if now.month == 12:
        next_reset = now.replace(year=now.year + 1, month=1, day=1)
    else:
        next_reset = now.replace(month=now.month + 1, day=1)
    
    next_reset = next_reset.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return (next_reset - now).days


def _determine_billing_cycle(tenant: Tenant) -> str:
    """Determine if tenant is on monthly or yearly billing."""
    if not tenant.current_period_start or not tenant.current_period_end:
        return "monthly"
    
    # Calculate period duration
    duration_days = (tenant.current_period_end - tenant.current_period_start).days
    
    if duration_days > 32:  # More than a month suggests yearly
        return "yearly"
    return "monthly"


# ─── Public Routes ──────────────────────────────────────────────────────────────

@router.get("/plans", response_model=list[PlanResponse])
def get_available_plans(db: Session = Depends(get_db)):
    """Get all available subscription plans for display."""
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.sort_order).all()
    
    return [_plan_to_response(plan) for plan in plans]


@router.get("", response_model=FullSubscriptionResponse)
def get_my_subscription(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get full subscription details for the current tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Ensure monthly usage is reset if needed
    _ensure_monthly_reset(tenant)
    db.commit()
    
    # Get current plan
    plan = tenant.plan
    if not plan:
        # Fallback to free plan if no plan assigned
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "free").first()
        if not plan:
            raise HTTPException(status_code=500, detail="No subscription plan found")
    
    limits = _get_plan_limits(plan)
    
    # Calculate storage
    actual_storage = _calculate_storage_usage(db, tenant.id)
    if tenant.storage_used_bytes != actual_storage:
        tenant.storage_used_bytes = actual_storage
        db.commit()
    
    # Build current plan response
    billing_cycle = _determine_billing_cycle(tenant)
    price = plan.price_yearly if billing_cycle == "yearly" else plan.price_monthly
    
    current_plan = CurrentPlanResponse(
        plan=_plan_to_response(plan),
        status=tenant.subscription_status,
        billing_cycle=billing_cycle,
        current_period_start=tenant.current_period_start.isoformat() if tenant.current_period_start else None,
        current_period_end=tenant.current_period_end.isoformat() if tenant.current_period_end else None,
        price=price,
    )
    
    # Build usage response
    analyses_limit = limits.get("analyses_per_month", 20)
    storage_limit = limits.get("storage_gb", 1)
    team_limit = limits.get("team_members", 1)
    
    # Count team members
    team_count = db.query(func.count(Tenant.id)).filter(
        Tenant.id == tenant.id
    ).scalar() or 1
    # Actually count users in tenant
    from app.backend.models.db_models import User as UserModel
    team_count = db.query(func.count(UserModel.id)).filter(
        UserModel.tenant_id == tenant.id
    ).scalar() or 1
    
    usage = UsageResponse(
        analyses_used=tenant.analyses_count_this_month,
        analyses_limit=analyses_limit if analyses_limit > 0 else float('inf'),
        storage_used_mb=tenant.storage_used_bytes / (1024 * 1024),
        storage_limit_gb=storage_limit,
        team_members_count=team_count,
        team_members_limit=team_limit,
        percent_used=min(
            (tenant.analyses_count_this_month / analyses_limit * 100) if analyses_limit > 0 else 0,
            100
        ),
    )
    
    # Get all available plans
    all_plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.sort_order).all()
    
    return FullSubscriptionResponse(
        current_plan=current_plan,
        usage=usage,
        available_plans=[_plan_to_response(p) for p in all_plans],
        days_until_reset=_calculate_days_until_reset(tenant),
    )


@router.get("/check/{action}", response_model=UsageCheckResponse)
def check_usage(
    action: str,
    quantity: int = 1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Check if a specific action would exceed usage limits.
    
    Actions:
    - resume_analysis: Single resume analysis
    - batch_analysis: Batch resume analysis (quantity = batch size)
    - storage_upload: File upload (not counted against monthly limit)
    """
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Ensure monthly usage is reset if needed
    _ensure_monthly_reset(tenant)
    db.commit()
    
    plan = tenant.plan
    if not plan:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "free").first()
    
    if not plan:
        return UsageCheckResponse(
            allowed=False,
            current_usage=0,
            limit=0,
            message="No subscription plan found"
        )
    
    limits = _get_plan_limits(plan)
    
    # Check based on action type
    if action in ["resume_analysis", "batch_analysis"]:
        analyses_limit = limits.get("analyses_per_month", 20)
        
        if analyses_limit < 0:  # Unlimited
            return UsageCheckResponse(
                allowed=True,
                current_usage=tenant.analyses_count_this_month,
                limit=-1,
            )
        
        projected_usage = tenant.analyses_count_this_month + quantity
        
        if projected_usage > analyses_limit:
            remaining = analyses_limit - tenant.analyses_count_this_month
            return UsageCheckResponse(
                allowed=False,
                current_usage=tenant.analyses_count_this_month,
                limit=analyses_limit,
                message=f"Usage limit exceeded. Remaining: {remaining}, Requested: {quantity}"
            )
        
        return UsageCheckResponse(
            allowed=True,
            current_usage=tenant.analyses_count_this_month,
            limit=analyses_limit,
        )
    
    elif action == "storage_upload":
        storage_limit_gb = limits.get("storage_gb", 1)
        storage_limit_bytes = storage_limit_gb * 1024 * 1024 * 1024
        
        if tenant.storage_used_bytes >= storage_limit_bytes:
            return UsageCheckResponse(
                allowed=False,
                current_usage=int(tenant.storage_used_bytes / (1024 * 1024)),
                limit=storage_limit_gb * 1024,
                message=f"Storage limit exceeded. Limit: {storage_limit_gb}GB"
            )
        
        return UsageCheckResponse(
            allowed=True,
            current_usage=int(tenant.storage_used_bytes / (1024 * 1024)),
            limit=storage_limit_gb * 1024,
        )
    
    # Unknown action - allow by default
    return UsageCheckResponse(
        allowed=True,
        current_usage=0,
        limit=-1,
    )


@router.get("/usage-history")
def get_usage_history(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get recent usage history for the tenant."""
    logs = db.query(UsageLog).filter(
        UsageLog.tenant_id == user.tenant_id
    ).order_by(UsageLog.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "action": log.action,
            "quantity": log.quantity,
            "details": json.loads(log.details) if log.details else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "user_email": log.user.email if log.user else None,
        }
        for log in logs
    ]


# ─── Admin Routes ─────────────────────────────────────────────────────────────

@router.post("/admin/reset-usage")
def admin_reset_usage(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Admin: Reset usage counters for the tenant (useful for testing)."""
    tenant = db.query(Tenant).filter(Tenant.id == admin.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    old_count = tenant.analyses_count_this_month
    tenant.analyses_count_this_month = 0
    tenant.usage_reset_at = datetime.now(timezone.utc)
    db.commit()
    
    return {
        "message": "Usage counters reset",
        "previous_count": old_count,
        "new_count": 0,
    }


@router.post("/admin/change-plan/{plan_id}")
def admin_change_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Admin: Change subscription plan (useful for testing plan features)."""
    tenant = db.query(Tenant).filter(Tenant.id == admin.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    new_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not new_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    old_plan_name = tenant.plan.name if tenant.plan else "none"
    tenant.plan_id = plan_id
    tenant.subscription_status = "active"
    tenant.current_period_start = datetime.now(timezone.utc)
    tenant.current_period_end = datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 1)
    tenant.subscription_updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {
        "message": "Plan changed successfully",
        "previous_plan": old_plan_name,
        "new_plan": new_plan.name,
        "new_plan_display": new_plan.display_name,
    }


# ─── Internal Helpers (used by other routes) ───────────────────────────────────

def record_usage(
    db: Session,
    tenant_id: int,
    user_id: int,
    action: str,
    quantity: int = 1,
    details: Optional[dict] = None
) -> bool:
    """Record usage and increment tenant counter. Returns True if successful.
    
    This function should be called from analyze routes after successful analysis.
    """
    try:
        # Get tenant and check limits
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return False
        
        # Ensure monthly reset
        _ensure_monthly_reset(tenant)
        
        # Check plan limits
        plan = tenant.plan
        if plan:
            limits = _get_plan_limits(plan)
            analyses_limit = limits.get("analyses_per_month", 20)
            
            if analyses_limit >= 0:  # Not unlimited
                if tenant.analyses_count_this_month + quantity > analyses_limit:
                    return False  # Would exceed limit
        
        # Increment counter
        tenant.analyses_count_this_month += quantity
        
        # Log the usage
        usage_log = UsageLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            quantity=quantity,
            details=json.dumps(details) if details else None,
        )
        db.add(usage_log)
        
        db.commit()
        return True
    
    except Exception:
        db.rollback()
        return False
