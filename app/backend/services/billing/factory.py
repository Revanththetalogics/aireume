"""Factory for creating the active payment provider from platform_configs."""
from typing import Optional

from sqlalchemy.orm import Session

from app.backend.models.db_models import PlatformConfig
from app.backend.services.billing.base import PaymentProvider
from app.backend.services.billing.manual_provider import ManualProvider
from app.backend.services.billing.stripe_provider import StripeProvider
from app.backend.services.billing.razorpay_provider import RazorpayProvider


# Mapping of provider name → (class, required config keys)
PROVIDER_REGISTRY = {
    "stripe": {
        "class": StripeProvider,
        "config_keys": [
            "billing.stripe.api_key",
            "billing.stripe.webhook_secret",
        ],
    },
    "razorpay": {
        "class": RazorpayProvider,
        "config_keys": [
            "billing.razorpay.key_id",
            "billing.razorpay.key_secret",
            "billing.razorpay.webhook_secret",
        ],
    },
    "manual": {
        "class": ManualProvider,
        "config_keys": [],
    },
}


def get_payment_provider(db: Session) -> PaymentProvider:
    """Instantiate and return the currently active payment provider.

    Reads ``billing.active_provider`` from the ``platform_configs`` table.
    Falls back to :class:`ManualProvider` when the key is missing or
    the configured provider is unknown.
    """
    # Determine active provider name
    active_row = (
        db.query(PlatformConfig)
        .filter(PlatformConfig.config_key == "billing.active_provider")
        .first()
    )
    provider_name = active_row.config_value if active_row else "manual"

    # Look up provider in registry
    provider_entry = PROVIDER_REGISTRY.get(provider_name)
    if provider_entry is None:
        # Unknown provider — fall back to manual
        return ManualProvider(db=db)

    provider_cls = provider_entry["class"]
    config_keys = provider_entry["config_keys"]

    # If this is the manual provider, just pass db
    if provider_name == "manual":
        return ManualProvider(db=db)

    # Load provider-specific config values from platform_configs
    config_rows = (
        db.query(PlatformConfig)
        .filter(PlatformConfig.config_key.in_(config_keys))
        .all()
    )
    config_map = {r.config_key: r.config_value for r in config_rows}

    # Build constructor kwargs from config
    kwargs = {}
    for key in config_keys:
        # Convert e.g. "billing.stripe.api_key" → "api_key"
        short_key = key.split(".")[-1]
        # Also map webhook_secret
        if "webhook_secret" in short_key:
            kwargs["webhook_secret"] = config_map.get(key, "")
        elif "api_key" in short_key:
            kwargs["api_key"] = config_map.get(key, "")
        elif "key_id" in short_key:
            kwargs["key_id"] = config_map.get(key, "")
        elif "key_secret" in short_key:
            kwargs["key_secret"] = config_map.get(key, "")
        else:
            kwargs[short_key] = config_map.get(key, "")

    return provider_cls(**kwargs)
