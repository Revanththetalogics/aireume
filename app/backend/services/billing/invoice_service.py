"""Invoice generation and retrieval service.

Generates sequential invoice numbers and creates invoice records
when a payment succeeds via any provider (Stripe, Razorpay, Manual).
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.models.db_models import Invoice

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
