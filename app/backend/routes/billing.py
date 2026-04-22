"""Billing routes — checkout, webhooks, subscription management."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user, require_platform_admin
from app.backend.models.db_models import User, Tenant
from app.backend.services.billing.factory import get_payment_provider

router = APIRouter(prefix="/api/billing", tags=["billing"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: str
    success_url: str = ""
    cancel_url: str = ""


class WebhookResponse(BaseModel):
    received: bool = True


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _require_tenant_access(current_user: User, tenant_id: int):
    """Ensure the user belongs to the requested tenant or is a platform admin."""
    if getattr(current_user, "is_platform_admin", False):
        return
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied for this tenant")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/checkout")
def create_checkout_session(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a checkout session for the current user's tenant."""
    provider = get_payment_provider(db)
    result = provider.create_checkout_session(
        tenant_id=current_user.tenant_id,
        plan=body.plan,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
    )
    return result


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Handle incoming webhook events from the payment provider.

    No authentication — the provider validates the payload via signature.
    """
    body = await request.body()
    signature = request.headers.get("X-Signature", "")
    provider = get_payment_provider(db)
    result = provider.handle_webhook_event(body, signature)
    return result


@router.get("/subscription/{tenant_id}")
def get_subscription_status(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get subscription status for a tenant.

    Requires admin or same-tenant membership.
    """
    _require_tenant_access(current_user, tenant_id)

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    subscription_id = tenant.stripe_subscription_id or f"manual_{tenant.id}"
    provider = get_payment_provider(db)
    return provider.get_subscription_status(tenant_id, subscription_id)


@router.post("/cancel/{tenant_id}")
def cancel_subscription(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel subscription for a tenant.

    Requires admin or same-tenant membership.
    """
    _require_tenant_access(current_user, tenant_id)

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    subscription_id = tenant.stripe_subscription_id or f"manual_{tenant.id}"
    provider = get_payment_provider(db)
    result = provider.cancel_subscription(tenant_id, subscription_id)
    return result
