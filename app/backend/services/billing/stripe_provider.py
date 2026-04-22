"""Stripe payment provider implementation."""
from typing import Dict, Any

from app.backend.services.billing.base import PaymentProvider

try:
    import stripe  # type: ignore
except ImportError:
    stripe = None


class StripeProvider(PaymentProvider):
    """Payment provider backed by Stripe.

    Requires the ``stripe`` Python package to be installed.  All methods
    raise a clear error when the dependency is missing.
    """

    def __init__(self, api_key: str = "", webhook_secret: str = ""):
        self._api_key = api_key
        self._webhook_secret = webhook_secret
        if stripe is not None and api_key:
            stripe.api_key = api_key

    def _require_stripe(self):
        if stripe is None:
            raise RuntimeError(
                "The 'stripe' package is not installed. "
                "Install it with: pip install stripe"
            )

    @property
    def provider_name(self) -> str:
        return "stripe"

    def create_checkout_session(
        self,
        tenant_id: int,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        self._require_stripe()
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": plan, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"tenant_id": tenant_id},
        )
        return {
            "session_id": session.id,
            "url": session.url,
            "provider": self.provider_name,
        }

    def cancel_subscription(
        self,
        tenant_id: int,
        subscription_id: str,
    ) -> Dict[str, Any]:
        self._require_stripe()
        sub = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
        return {
            "subscription_id": sub.id,
            "status": sub.status,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "provider": self.provider_name,
        }

    def get_subscription_status(
        self,
        tenant_id: int,
        subscription_id: str,
    ) -> Dict[str, Any]:
        self._require_stripe()
        sub = stripe.Subscription.retrieve(subscription_id)
        return {
            "subscription_id": sub.id,
            "status": sub.status,
            "current_period_end": sub.current_period_end,
            "provider": self.provider_name,
        }

    def handle_webhook_event(
        self,
        payload: bytes,
        signature: str,
    ) -> Dict[str, Any]:
        self._require_stripe()
        event = stripe.Webhook.construct_event(
            payload, signature, self._webhook_secret
        )
        return {
            "event_type": event["type"],
            "data": event["data"],
            "provider": self.provider_name,
        }
