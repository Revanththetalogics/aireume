"""Billing routes — checkout, webhooks, subscription management."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user, require_platform_admin
from app.backend.models.db_models import User, Tenant, Invoice
from app.backend.services.billing.factory import get_payment_provider
from app.backend.services.billing.invoice_service import get_tenant_invoices, get_tenant_invoice_count, get_invoice_by_id
from app.backend.services.billing.webhook_processor import process_webhook_event

log = logging.getLogger(__name__)

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
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    provider = get_payment_provider(db)
    result = provider.create_checkout_session(
        tenant_id=current_user.tenant_id,
        plan=body.plan,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        stripe_customer_id=tenant.stripe_customer_id if tenant and tenant.stripe_customer_id else "",
    )
    return result


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Handle incoming webhook events from the payment provider.

    No authentication — the provider validates the payload via signature.
    Always returns 200 to prevent provider-side retries.  Errors are
    logged internally.
    """
    try:
        body = await request.body()
        signature = request.headers.get("X-Signature", "")
        provider = get_payment_provider(db)

        # Verify signature and parse event
        result = provider.handle_webhook_event(body, signature)

        provider_name = result.get("provider", provider.provider_name)
        event_type = result.get("event_type", "unknown")
        event_id = result.get("event_id")
        data = result.get("data", {})

        # Process the event — updates tenant state, logs audit, fires webhooks
        raw_payload = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)
        process_result = process_webhook_event(
            db,
            provider=provider_name,
            event_type=event_type,
            data=data,
            raw_payload=raw_payload,
            event_id=event_id,
        )

        log.info(
            "Webhook processed: provider=%s event=%s result=%s",
            provider_name, event_type, process_result.get("reason", "ok"),
        )
    except Exception as exc:
        # Always return 200 — log errors internally
        log.exception("Webhook processing error: %s", exc)
    finally:
        # Ensure the session is clean even if an error occurred mid-transaction
        try:
            db.rollback()
        except Exception:
            pass

    return {"received": True}


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


@router.get("/invoices")
def list_invoices(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get invoices for the current tenant.

    Any authenticated user can see their own tenant's invoices.
    Returns a paginated list ordered by newest first.
    """
    invoices = get_tenant_invoices(db, tenant_id=current_user.tenant_id, limit=limit, offset=offset)
    total = get_tenant_invoice_count(db, tenant_id=current_user.tenant_id)

    return {
        "invoices": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "status": inv.status,
                "amount": inv.amount,
                "currency": inv.currency,
                "description": inv.description,
                "line_items": inv.line_items,
                "payment_provider": inv.payment_provider,
                "period_start": inv.period_start.isoformat() if inv.period_start else None,
                "period_end": inv.period_end.isoformat() if inv.period_end else None,
                "issued_at": inv.issued_at.isoformat() if inv.issued_at else None,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
            }
            for inv in invoices
        ],
        "total": total,
    }


@router.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single invoice detail.

    Only returns the invoice if it belongs to the current user's tenant.
    """
    invoice = get_invoice_by_id(db, invoice_id=invoice_id, tenant_id=current_user.tenant_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status,
        "amount": invoice.amount,
        "currency": invoice.currency,
        "description": invoice.description,
        "line_items": invoice.line_items,
        "payment_provider": invoice.payment_provider,
        "provider_invoice_id": invoice.provider_invoice_id,
        "period_start": invoice.period_start.isoformat() if invoice.period_start else None,
        "period_end": invoice.period_end.isoformat() if invoice.period_end else None,
        "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
    }
