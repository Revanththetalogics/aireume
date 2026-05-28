"""
Webhook Event Registry.

Provides a public endpoint that lists all available webhook event types,
their descriptions, and example payloads so integrators can self-document
their webhook integrations without reading source code.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

WEBHOOK_EVENTS = [
    {
        "event": "subscription.changed",
        "description": "Fired when a tenant's subscription plan or status changes.",
        "example_payload": {
            "tenant_id": 1,
            "old_plan": "free",
            "new_plan": "pro",
            "status": "active",
        },
    },
    {
        "event": "usage.threshold_reached",
        "description": "Fired when a tenant reaches 80% or 100% of a usage quota.",
        "example_payload": {
            "tenant_id": 1,
            "metric": "analyses_per_month",
            "threshold_percent": 80,
            "current_value": 80,
            "limit": 100,
        },
    },
    {
        "event": "dunning.started",
        "description": "Fired when payment fails and the dunning retry process begins.",
        "example_payload": {
            "tenant_id": 1,
            "failure_reason": "card_declined",
            "retry_count": 1,
        },
    },
    {
        "event": "dunning.resolved",
        "description": "Fired when dunning is resolved after a successful payment.",
        "example_payload": {
            "tenant_id": 1,
            "resolved_at": "2026-05-28T10:00:00Z",
        },
    },
    {
        "event": "dunning.exhausted",
        "description": "Fired when all dunning retries are exhausted.",
        "example_payload": {
            "tenant_id": 1,
            "total_retries": 4,
        },
    },
    {
        "event": "tenant.suspended",
        "description": "Fired when a tenant account is suspended.",
        "example_payload": {
            "tenant_id": 1,
            "reason": "payment_failure",
        },
    },
    {
        "event": "tenant.reactivated",
        "description": "Fired when a suspended tenant is reactivated.",
        "example_payload": {
            "tenant_id": 1,
        },
    },
]

SIGNING_INFO = {
    "algorithm": "HMAC-SHA256",
    "header": "X-Webhook-Signature",
    "description": (
        "Each delivery includes an X-Webhook-Signature header containing "
        "a hex-encoded HMAC-SHA256 digest of the raw request body, "
        "computed using the webhook secret configured at registration."
    ),
}


@router.get("/events")
def list_webhook_events():
    """Return all available webhook event types with descriptions and example payloads."""
    return {
        "events": WEBHOOK_EVENTS,
        "signing": SIGNING_INFO,
    }
