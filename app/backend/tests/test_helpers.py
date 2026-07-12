"""
Shared test utilities that can be safely imported by test modules
without triggering conftest.py re-initialization.
"""
from app.backend.db import database


def _verify_user_via_api(email: str):
    """Mark a user's email as verified via the DB session.

    Uses ``database.SessionLocal`` which is set to ``TestingSessionLocal``
    by conftest.py at startup, so it always targets the in-memory test DB
    regardless of which module scope the caller lives in.
    """
    from app.backend.models.db_models import User
    db = database.SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.email_verified = True
            db.commit()
    finally:
        db.close()


def resolve_plan(db, *names: str):
    """Look up a subscription plan by name, supporting legacy aliases (e.g. pro → growth)."""
    from app.backend.models.db_models import SubscriptionPlan
    return db.query(SubscriptionPlan).filter(
        SubscriptionPlan.name.in_(names),
        SubscriptionPlan.is_active == True,
    ).first()


def assign_tenant_plan(db, *plan_names: str, slug=None, tenant_id=None, email=None):
    """Assign a subscription plan to a tenant (by slug, id, or user email)."""
    from app.backend.models.db_models import Tenant, User
    from app.backend.services.feature_flag_service import invalidate_cache

    tenant = None
    if tenant_id is not None:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    elif slug:
        tenant = db.query(Tenant).filter(Tenant.slug == slug).first()
    elif email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()

    if tenant is None:
        raise ValueError("assign_tenant_plan: tenant not found")

    plan = resolve_plan(db, *plan_names)
    if plan is None:
        raise ValueError(f"assign_tenant_plan: no plan matching {plan_names!r}")

    tenant.plan_id = plan.id
    tenant.subscription_status = "active"
    db.commit()
    invalidate_cache(tenant.id)
    return tenant
