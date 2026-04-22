"""Manual / enterprise-invoicing payment provider.

This provider works entirely offline — no external API keys or SDKs
required.  It is the default when no payment provider is configured,
and is suitable for enterprise customers who pay via invoice / PO.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.backend.models.db_models import Tenant
from app.backend.services.billing.base import PaymentProvider


class ManualProvider(PaymentProvider):
    """Offline / manual-invoicing payment provider.

    All operations are recorded in the local database.  No external
    dependencies are required.
    """

    def __init__(self, db: Session = None):
        self._db = db

    @property
    def provider_name(self) -> str:
        return "manual"

    def create_checkout_session(
        self,
        tenant_id: int,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        reference_id = f"manual_{uuid.uuid4().hex[:12]}"
        return {
            "reference_id": reference_id,
            "provider": self.provider_name,
            "plan": plan,
            "tenant_id": tenant_id,
            "message": "Manual checkout created. Subscription will be activated by an administrator.",
        }

    def cancel_subscription(
        self,
        tenant_id: int,
        subscription_id: str,
    ) -> Dict[str, Any]:
        result = {
            "subscription_id": subscription_id,
            "status": "cancelled",
            "provider": self.provider_name,
        }

        if self._db is not None:
            tenant = self._db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                tenant.subscription_status = "cancelled"
                self._db.commit()

        return result

    def get_subscription_status(
        self,
        tenant_id: int,
        subscription_id: str,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "subscription_id": subscription_id,
            "provider": self.provider_name,
        }

        if self._db is not None:
            tenant = self._db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                result["status"] = tenant.subscription_status
                result["current_period_end"] = (
                    tenant.current_period_end.isoformat()
                    if tenant.current_period_end
                    else None
                )
                return result

        result["status"] = "unknown"
        result["current_period_end"] = None
        return result

    def handle_webhook_event(
        self,
        payload: bytes,
        signature: str,
    ) -> Dict[str, Any]:
        # Manual provider does not receive external webhooks — no-op.
        return {
            "event_type": "manual.noop",
            "data": {},
            "provider": self.provider_name,
        }
