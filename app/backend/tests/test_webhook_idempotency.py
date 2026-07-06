"""
Tests billing webhook idempotency: a provider event with a (provider, event_id)
that has already been processed successfully must not be handled twice
(protects against Stripe/Razorpay retries and replay attacks).
"""
import pytest

from app.backend.services.billing.webhook_processor import process_webhook_event
from app.backend.models.db_models import BillingEvent


class TestWebhookIdempotency:
    def test_duplicate_event_id_is_ignored(self, db):
        # Pre-existing successfully-processed event
        db.add(BillingEvent(
            provider="stripe",
            event_id="evt_dup_1",
            event_type="invoice.paid",
            result="success",
            raw_payload="{}",
        ))
        db.commit()

        result = process_webhook_event(
            db,
            provider="stripe",
            event_type="invoice.paid",
            data={},
            raw_payload="{}",
            event_id="evt_dup_1",
        )
        assert result["processed"] is False
        assert result["reason"] == "duplicate"

    def test_new_event_id_is_not_treated_as_duplicate(self, db):
        # Unknown event_type but new event_id → not a duplicate (processed/ignored,
        # but never "duplicate").
        result = process_webhook_event(
            db,
            provider="stripe",
            event_type="some.unhandled.event",
            data={},
            raw_payload="{}",
            event_id="evt_new_1",
        )
        assert result["reason"] != "duplicate"

    def test_same_event_id_different_provider_not_duplicate(self, db):
        db.add(BillingEvent(
            provider="stripe", event_id="evt_x", event_type="invoice.paid",
            result="success", raw_payload="{}",
        ))
        db.commit()

        result = process_webhook_event(
            db,
            provider="razorpay",
            event_type="invoice.paid",
            data={},
            raw_payload="{}",
            event_id="evt_x",
        )
        assert result["reason"] != "duplicate"

    def test_previously_errored_event_is_not_treated_as_duplicate(self, db):
        """Only successful events dedupe; a prior error should allow reprocessing."""
        db.add(BillingEvent(
            provider="stripe", event_id="evt_err", event_type="invoice.paid",
            result="error", raw_payload="{}",
        ))
        db.commit()

        result = process_webhook_event(
            db,
            provider="stripe",
            event_type="invoice.paid",
            data={},
            raw_payload="{}",
            event_id="evt_err",
        )
        assert result.get("reason") != "duplicate"
