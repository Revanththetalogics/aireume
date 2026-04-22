"""Razorpay payment provider implementation."""
from typing import Dict, Any

from app.backend.services.billing.base import PaymentProvider

try:
    import razorpay  # type: ignore
except ImportError:
    razorpay = None


class RazorpayProvider(PaymentProvider):
    """Payment provider backed by Razorpay.

    Requires the ``razorpay`` Python package to be installed.  All methods
    raise a clear error when the dependency is missing.
    """

    def __init__(self, key_id: str = "", key_secret: str = "", webhook_secret: str = ""):
        self._key_id = key_id
        self._key_secret = key_secret
        self._webhook_secret = webhook_secret
        self._client = None
        if razorpay is not None and key_id and key_secret:
            self._client = razorpay.Client(auth=(key_id, key_secret))

    def _require_client(self):
        if razorpay is None:
            raise RuntimeError(
                "The 'razorpay' package is not installed. "
                "Install it with: pip install razorpay"
            )
        if self._client is None:
            raise RuntimeError(
                "Razorpay client not configured. Provide key_id and key_secret."
            )

    @property
    def provider_name(self) -> str:
        return "razorpay"

    def create_checkout_session(
        self,
        tenant_id: int,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        self._require_client()
        order = self._client.order.create({
            "amount": 0,  # amount set by plan on Razorpay dashboard
            "currency": "USD",
            "receipt": f"tenant_{tenant_id}_plan_{plan}",
            "notes": {"tenant_id": str(tenant_id), "plan": plan},
        })
        return {
            "order_id": order["id"],
            "key_id": self._key_id,
            "provider": self.provider_name,
        }

    def cancel_subscription(
        self,
        tenant_id: int,
        subscription_id: str,
    ) -> Dict[str, Any]:
        self._require_client()
        sub = self._client.subscription.cancel(subscription_id)
        return {
            "subscription_id": sub["id"],
            "status": sub.get("status", "cancelled"),
            "provider": self.provider_name,
        }

    def get_subscription_status(
        self,
        tenant_id: int,
        subscription_id: str,
    ) -> Dict[str, Any]:
        self._require_client()
        sub = self._client.subscription.fetch(subscription_id)
        return {
            "subscription_id": sub["id"],
            "status": sub.get("status", "unknown"),
            "current_period_end": sub.get("current_end"),
            "provider": self.provider_name,
        }

    def handle_webhook_event(
        self,
        payload: bytes,
        signature: str,
    ) -> Dict[str, Any]:
        self._require_client()
        self._client.utility.verify_webhook_signature(
            payload.decode("utf-8") if isinstance(payload, bytes) else payload,
            signature,
            self._webhook_secret,
        )
        import json
        event = json.loads(payload)
        return {
            "event_type": event.get("event", "unknown"),
            "data": event.get("payload", {}),
            "provider": self.provider_name,
        }
