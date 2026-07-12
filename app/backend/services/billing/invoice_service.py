"""Invoice generation and retrieval service.

Generates sequential invoice numbers and creates invoice records
when a payment succeeds via any provider (Stripe, Razorpay, Manual).
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.backend.models.db_models import Invoice, Tenant

log = logging.getLogger(__name__)


def generate_invoice_number(db: Session) -> str:
    """Generate a sequential invoice number like INV-2026-00001.

    The sequence resets each calendar year.  We look up the highest
    existing number for the current year and increment by one.
    """
    year = datetime.now(timezone.utc).year
    prefix = f"INV-{year}-"

    # Find the max invoice_number with this prefix
    last_invoice = (
        db.query(Invoice.invoice_number)
        .filter(Invoice.invoice_number.like(f"{prefix}%"))
        .order_by(Invoice.invoice_number.desc())
        .first()
    )

    if last_invoice is None:
        seq = 1
    else:
        # Extract the numeric suffix from e.g. "INV-2026-00001"
        try:
            seq = int(last_invoice[0].split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1

    return f"{prefix}{seq:05d}"


def create_invoice_from_payment(
    db: Session,
    *,
    tenant_id: int,
    amount: int,
    currency: str = "usd",
    plan_name: str = "",
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
    payment_provider: Optional[str] = None,
    provider_invoice_id: Optional[str] = None,
    description: Optional[str] = None,
) -> Invoice:
    """Create an invoice record after a successful payment.

    The caller is responsible for calling ``db.commit()`` afterwards
    (typically the webhook handler that already manages its own transaction).
    """
    invoice_number = generate_invoice_number(db)

    line_items = [
        {
            "description": plan_name or "Subscription payment",
            "amount": amount,
            "quantity": 1,
        }
    ]

    now = datetime.now(timezone.utc)

    invoice = Invoice(
        tenant_id=tenant_id,
        invoice_number=invoice_number,
        status="paid",
        amount=amount,
        currency=currency.lower(),
        description=description or plan_name or "Subscription payment",
        line_items=line_items,
        payment_provider=payment_provider,
        provider_invoice_id=provider_invoice_id,
        period_start=period_start,
        period_end=period_end,
        paid_at=now,
    )
    db.add(invoice)
    db.flush()  # assign id without committing
    log.info(
        "Created invoice %s for tenant_id=%s amount=%d%s provider=%s",
        invoice_number, tenant_id, amount, currency, payment_provider,
    )
    return invoice


def get_tenant_invoices(
    db: Session,
    tenant_id: int,
    limit: int = 50,
    offset: int = 0,
) -> List[Invoice]:
    """Get paginated invoices for a tenant, newest first."""
    return (
        db.query(Invoice)
        .filter(Invoice.tenant_id == tenant_id)
        .order_by(Invoice.issued_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_tenant_invoice_count(db: Session, tenant_id: int) -> int:
    """Get total invoice count for a tenant."""
    return (
        db.query(func.count(Invoice.id))
        .filter(Invoice.tenant_id == tenant_id)
        .scalar()
        or 0
    )


def get_invoice_by_id(db: Session, invoice_id: int, tenant_id: int) -> Optional[Invoice]:
    """Get a single invoice, ensuring it belongs to the given tenant."""
    return (
        db.query(Invoice)
        .filter(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
        .first()
    )


def _serialize_invoice(inv: Invoice, tenant_name: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": inv.id,
        "tenant_id": inv.tenant_id,
        "tenant_name": tenant_name,
        "invoice_number": inv.invoice_number,
        "status": inv.status,
        "amount": inv.amount,
        "currency": inv.currency,
        "description": inv.description,
        "line_items": inv.line_items or [],
        "payment_provider": inv.payment_provider,
        "provider_invoice_id": inv.provider_invoice_id,
        "period_start": inv.period_start.isoformat() if inv.period_start else None,
        "period_end": inv.period_end.isoformat() if inv.period_end else None,
        "issued_at": inv.issued_at.isoformat() if inv.issued_at else None,
        "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
    }


def get_all_invoices(
    db: Session,
    *,
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    tenant_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Platform-admin view of invoices across all tenants."""
    q = (
        db.query(Invoice, Tenant.name.label("tenant_name"))
        .join(Tenant, Tenant.id == Invoice.tenant_id)
        .order_by(Invoice.issued_at.desc())
    )
    if status:
        q = q.filter(Invoice.status == status)
    if tenant_id:
        q = q.filter(Invoice.tenant_id == tenant_id)
    rows = q.offset(offset).limit(limit).all()
    return [_serialize_invoice(inv, tenant_name) for inv, tenant_name in rows]


def get_revenue_metrics(db: Session) -> Dict[str, Any]:
    """Compute MRR/ARR from paid invoices in the last 30 days (actual collected revenue)."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = now - timedelta(days=30)

    collected_this_month = (
        db.query(func.coalesce(func.sum(Invoice.amount), 0))
        .filter(Invoice.status == "paid", Invoice.paid_at >= month_start)
        .scalar()
        or 0
    )

    collected_last_30_days = (
        db.query(func.coalesce(func.sum(Invoice.amount), 0))
        .filter(Invoice.status == "paid", Invoice.paid_at >= thirty_days_ago)
        .scalar()
        or 0
    )

    outstanding = (
        db.query(func.coalesce(func.sum(Invoice.amount), 0))
        .filter(Invoice.status.in_(["pending", "overdue"]))
        .scalar()
        or 0
    )

    return {
        "mrr_cents": int(collected_last_30_days),
        "arr_estimate_cents": int(collected_last_30_days) * 12,
        "collected_this_month_cents": int(collected_this_month),
        "outstanding_cents": int(outstanding),
        "mrr": round(collected_last_30_days / 100, 2),
        "collected_this_month": round(collected_this_month / 100, 2),
    }
