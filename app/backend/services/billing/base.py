"""Abstract base class for payment provider implementations."""
from abc import ABC, abstractmethod
from typing import Dict, Any


class PaymentProvider(ABC):
    """Provider-agnostic interface for payment/billing operations.

    All payment providers (Stripe, Razorpay, Manual/enterprise invoicing)
    must implement this interface so the rest of the application remains
    decoupled from any specific payment gateway.
    """

    @abstractmethod
    def create_checkout_session(
        self,
        tenant_id: int,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        """Create a checkout session for a subscription purchase.

        Returns a dict with at least a ``session_id`` or ``reference_id``
        that the frontend can use to redirect the user.
        """

    @abstractmethod
    def cancel_subscription(
        self,
        tenant_id: int,
        subscription_id: str,
    ) -> Dict[str, Any]:
        """Cancel an active subscription.

        Returns a dict with the cancellation status.
        """

    @abstractmethod
    def get_subscription_status(
        self,
        tenant_id: int,
        subscription_id: str,
    ) -> Dict[str, Any]:
        """Retrieve the current status of a subscription.

        Returns a dict with at least ``status`` and ``current_period_end``.
        """

    @abstractmethod
    def handle_webhook_event(
        self,
        payload: bytes,
        signature: str,
    ) -> Dict[str, Any]:
        """Validate and process an incoming webhook from the provider.

        Returns a normalised dict with ``event_type`` and ``data``.
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of this provider (e.g. 'stripe', 'razorpay')."""
