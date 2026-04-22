"""
Tests for webhook system: service layer + admin endpoints.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.backend.models.db_models import (
    Tenant, User, Webhook, WebhookDelivery, SubscriptionPlan,
)
from app.backend.services.webhook_service import (
    _sign_payload, dispatch_event, MAX_FAILURE_COUNT,
)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _make_tenant_and_admin(db):
    """Create a tenant + platform-admin user; return (tenant, admin)."""
    plan = SubscriptionPlan(
        name="free", display_name="Free", limits="{}", features="[]",
        price_monthly=0, price_yearly=0,
    )
    db.add(plan)
    db.flush()

    tenant = Tenant(name="HookCorp", slug="hookcorp", plan_id=plan.id)
    db.add(tenant)
    db.flush()

    admin = User(
        tenant_id=tenant.id,
        email="admin@hookcorp.com",
        hashed_password="x",
        is_platform_admin=True,
    )
    db.add(admin)
    db.commit()
    return tenant, admin


# ─── HMAC signature ────────────────────────────────────────────────────────

class TestHMACSignature:
    def test_hmac_signature(self):
        """Verify HMAC-SHA256 signature generation is deterministic and correct."""
        payload = '{"event":"test"}'
        secret = "mysecret"
        sig = _sign_payload(payload, secret)
        # Manually verify
        import hmac as _hmac, hashlib
        expected = _hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        assert sig == expected

    def test_hmac_signature_different_secrets(self):
        """Different secrets produce different signatures."""
        payload = '{"event":"test"}'
        sig1 = _sign_payload(payload, "secret1")
        sig2 = _sign_payload(payload, "secret2")
        assert sig1 != sig2


# ─── Service-level dispatch tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_dispatch_event_matching(db):
    """Webhook only fires for matching events."""
    tenant, _ = _make_tenant_and_admin(db)

    # Create webhook subscribed to "analysis.completed" only
    wh = Webhook(
        tenant_id=tenant.id,
        url="https://example.com/hook",
        secret="s3cret",
        events=json.dumps(["analysis.completed"]),
    )
    db.add(wh)
    db.commit()

    with patch("app.backend.services.webhook_service._send_webhook", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (200, "ok", True)

        # Dispatch matching event
        await dispatch_event(db, tenant.id, "analysis.completed", {"result_id": 1})
        assert mock_send.call_count == 1

    with patch("app.backend.services.webhook_service._send_webhook", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (200, "ok", True)

        # Dispatch non-matching event — webhook should NOT fire
        await dispatch_event(db, tenant.id, "subscription.changed", {"new_plan": "pro"})
        assert mock_send.call_count == 0


@pytest.mark.asyncio
async def test_dispatch_event_wildcard(db):
    """Webhook with '*' event matches everything."""
    tenant, _ = _make_tenant_and_admin(db)

    wh = Webhook(
        tenant_id=tenant.id,
        url="https://example.com/hook",
        secret="s3cret",
        events=json.dumps(["*"]),
    )
    db.add(wh)
    db.commit()

    with patch("app.backend.services.webhook_service._send_webhook", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (200, "ok", True)

        await dispatch_event(db, tenant.id, "any.event", {})
        assert mock_send.call_count == 1


@pytest.mark.asyncio
async def test_dispatch_event_records_delivery(db):
    """Delivery is recorded in the database on dispatch."""
    tenant, _ = _make_tenant_and_admin(db)

    wh = Webhook(
        tenant_id=tenant.id,
        url="https://example.com/hook",
        secret="s3cret",
        events=json.dumps(["*"]),
    )
    db.add(wh)
    db.commit()

    with patch("app.backend.services.webhook_service._send_webhook", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (200, "ok", True)

        await dispatch_event(db, tenant.id, "test.event", {"key": "value"})

    deliveries = db.query(WebhookDelivery).filter(WebhookDelivery.webhook_id == wh.id).all()
    assert len(deliveries) >= 1
    d = deliveries[0]
    assert d.event == "test.event"
    assert d.success is True
    assert d.response_status == 200
    assert d.attempt == 1

    # Webhook failure_count should be reset to 0
    db.refresh(wh)
    assert wh.failure_count == 0
    assert wh.last_triggered_at is not None


@pytest.mark.asyncio
async def test_dispatch_event_failed_delivery(db):
    """Failed delivery increments failure_count and records failed delivery."""
    tenant, _ = _make_tenant_and_admin(db)

    wh = Webhook(
        tenant_id=tenant.id,
        url="https://example.com/hook",
        secret="s3cret",
        events=json.dumps(["*"]),
    )
    db.add(wh)
    db.commit()

    with patch("app.backend.services.webhook_service._send_webhook", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (500, "error", False)
        # Short-circuit sleep to avoid delays in tests
        with patch("app.backend.services.webhook_service.asyncio.sleep", new_callable=AsyncMock):
            await dispatch_event(db, tenant.id, "test.fail", {})

    db.refresh(wh)
    assert wh.failure_count == 3  # MAX_RETRIES = 3
    assert wh.last_failure_at is not None

    deliveries = db.query(WebhookDelivery).filter(
        WebhookDelivery.webhook_id == wh.id,
        WebhookDelivery.success == False,
    ).all()
    assert len(deliveries) == 3


@pytest.mark.asyncio
async def test_auto_disable_after_failures(db):
    """Webhook is auto-disabled after MAX_FAILURE_COUNT consecutive failures."""
    tenant, _ = _make_tenant_and_admin(db)

    wh = Webhook(
        tenant_id=tenant.id,
        url="https://example.com/hook",
        secret="s3cret",
        events=json.dumps(["*"]),
        failure_count=MAX_FAILURE_COUNT - 3,  # Will reach MAX after 3 retries
    )
    db.add(wh)
    db.commit()

    with patch("app.backend.services.webhook_service._send_webhook", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (500, "error", False)
        with patch("app.backend.services.webhook_service.asyncio.sleep", new_callable=AsyncMock):
            await dispatch_event(db, tenant.id, "test.disable", {})

    db.refresh(wh)
    assert wh.is_active is False
    assert wh.failure_count >= MAX_FAILURE_COUNT


# ─── Admin endpoint tests ───────────────────────────────────────────────────

class TestWebhookEndpoints:
    """HTTP-level tests for webhook admin CRUD endpoints."""

    def test_create_webhook(self, platform_admin_client, db):
        tenant, admin = _make_tenant_and_admin(db)

        resp = platform_admin_client.post(
            f"/api/admin/tenants/{tenant.id}/webhooks",
            json={
                "url": "https://example.com/webhook",
                "secret": "myhooksecret",
                "events": ["analysis.completed", "subscription.changed"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://example.com/webhook"
        assert data["secret"] == "myhooksecret"
        assert "analysis.completed" in data["events"]
        assert "subscription.changed" in data["events"]
        assert "id" in data

    def test_create_webhook_auto_secret(self, platform_admin_client, db):
        """When no secret is provided, one is auto-generated."""
        tenant, _ = _make_tenant_and_admin(db)

        resp = platform_admin_client.post(
            f"/api/admin/tenants/{tenant.id}/webhooks",
            json={"url": "https://example.com/wh", "events": ["*"]},
        )
        assert resp.status_code == 200
        assert len(resp.json()["secret"]) > 0

    def test_list_webhooks(self, platform_admin_client, db):
        tenant, _ = _make_tenant_and_admin(db)

        # Create two webhooks
        for i in range(2):
            wh = Webhook(
                tenant_id=tenant.id,
                url=f"https://example.com/wh{i}",
                secret=f"secret{i}",
                events=json.dumps(["*"]),
            )
            db.add(wh)
        db.commit()

        resp = platform_admin_client.get(f"/api/admin/tenants/{tenant.id}/webhooks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all("id" in w for w in data)
        assert all("url" in w for w in data)

    def test_delete_webhook(self, platform_admin_client, db):
        tenant, _ = _make_tenant_and_admin(db)

        wh = Webhook(
            tenant_id=tenant.id,
            url="https://example.com/delete-me",
            secret="secret",
            events=json.dumps(["*"]),
        )
        db.add(wh)
        db.commit()
        wh_id = wh.id

        resp = platform_admin_client.delete(
            f"/api/admin/tenants/{tenant.id}/webhooks/{wh_id}"
        )
        assert resp.status_code == 200
        assert db.query(Webhook).filter(Webhook.id == wh_id).first() is None

    def test_delete_webhook_not_found(self, platform_admin_client, db):
        tenant, _ = _make_tenant_and_admin(db)

        resp = platform_admin_client.delete(
            f"/api/admin/tenants/{tenant.id}/webhooks/99999"
        )
        assert resp.status_code == 404

    def test_list_deliveries(self, platform_admin_client, db):
        tenant, _ = _make_tenant_and_admin(db)

        wh = Webhook(
            tenant_id=tenant.id,
            url="https://example.com/wh",
            secret="secret",
            events=json.dumps(["*"]),
        )
        db.add(wh)
        db.flush()

        # Create delivery records
        for i in range(3):
            d = WebhookDelivery(
                webhook_id=wh.id,
                event="test.event",
                payload="{}",
                response_status=200,
                success=True,
                attempt=1,
            )
            db.add(d)
        db.commit()

        resp = platform_admin_client.get(
            f"/api/admin/tenants/{tenant.id}/webhooks/{wh.id}/deliveries"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert all("event" in d for d in data)

    def test_webhook_requires_platform_admin(self, auth_client, db):
        """Regular user (non-platform-admin) gets 403."""
        tenant, _ = _make_tenant_and_admin(db)

        resp = auth_client.get(f"/api/admin/tenants/{tenant.id}/webhooks")
        assert resp.status_code == 403

    def test_create_webhook_tenant_not_found(self, platform_admin_client, db):
        resp = platform_admin_client.post(
            "/api/admin/tenants/99999/webhooks",
            json={"url": "https://example.com/wh", "events": ["*"]},
        )
        assert resp.status_code == 404

    def test_list_webhooks_tenant_not_found(self, platform_admin_client, db):
        resp = platform_admin_client.get("/api/admin/tenants/99999/webhooks")
        assert resp.status_code == 404

    def test_deliveries_webhook_not_found(self, platform_admin_client, db):
        tenant, _ = _make_tenant_and_admin(db)
        resp = platform_admin_client.get(
            f"/api/admin/tenants/{tenant.id}/webhooks/99999/deliveries"
        )
        assert resp.status_code == 404
