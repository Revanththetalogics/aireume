"""Webhook dispatch service with retry logic and HMAC signing."""
import hashlib
import hmac
import json
import logging
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.backend.models.db_models import Webhook, WebhookDelivery

log = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [1, 5, 30]  # seconds
MAX_FAILURE_COUNT = 10  # auto-disable after this many consecutive failures


def _sign_payload(payload_str: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    return hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()


async def _send_webhook(url: str, payload: dict, secret: str) -> tuple[int, str, bool]:
    """Send HTTP POST to webhook URL. Returns (status_code, body, success)."""
    import httpx

    payload_str = json.dumps(payload, default=str)
    signature = _sign_payload(payload_str, secret)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "User-Agent": "ARIA-Webhook/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, content=payload_str, headers=headers)
            success = 200 <= response.status_code < 300
            return response.status_code, response.text[:1000], success
    except Exception as e:
        log.warning("Webhook delivery failed to %s: %s", url, str(e))
        return 0, str(e)[:1000], False


async def dispatch_event(db: Session, tenant_id: int, event: str, payload: dict):
    """Dispatch a webhook event to all matching active webhooks for a tenant.

    This runs asynchronously and does not block the main request.
    """
    webhooks = (
        db.query(Webhook)
        .filter(Webhook.tenant_id == tenant_id, Webhook.is_active == True)
        .all()
    )

    for webhook in webhooks:
        # Check if this webhook subscribes to this event
        try:
            events = json.loads(webhook.events) if webhook.events else []
        except (json.JSONDecodeError, TypeError):
            events = []

        if event not in events and "*" not in events:
            continue

        # Attempt delivery with retries
        full_payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "data": payload,
        }

        success = False
        status_code = 0
        response_body = ""

        for attempt in range(1, MAX_RETRIES + 1):
            status_code, response_body, success = await _send_webhook(
                webhook.url, full_payload, webhook.secret
            )

            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                event=event,
                payload=json.dumps(full_payload, default=str),
                response_status=status_code,
                response_body=response_body,
                success=success,
                attempt=attempt,
            )
            db.add(delivery)

            if success:
                webhook.failure_count = 0
                webhook.last_triggered_at = datetime.now(timezone.utc)
                break
            else:
                webhook.failure_count += 1
                webhook.last_failure_at = datetime.now(timezone.utc)

                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAYS[attempt - 1])

        # Auto-disable after too many failures
        if webhook.failure_count >= MAX_FAILURE_COUNT:
            webhook.is_active = False
            log.warning("Webhook %d auto-disabled after %d failures", webhook.id, webhook.failure_count)

        db.commit()


def dispatch_event_background(db_factory, tenant_id: int, event: str, payload: dict):
    """Fire-and-forget wrapper that dispatches webhook in background.

    Use this from synchronous route handlers. Creates its own DB session.
    """
    async def _run():
        from app.backend.db import database
        db = database.SessionLocal()
        try:
            await dispatch_event(db, tenant_id, event, payload)
        except Exception as e:
            log.exception("Background webhook dispatch failed: %s", e)
        finally:
            db.close()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_run())
        else:
            asyncio.run(_run())
    except RuntimeError:
        # No event loop — skip webhook dispatch silently
        log.warning("No event loop available for webhook dispatch")
