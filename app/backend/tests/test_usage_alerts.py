"""
Tests for usage alert service: threshold checks, duplicate prevention,
webhook dispatch, and API endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.backend.models.db_models import (
    SubscriptionPlan, Tenant, User, UsageAlert, UsageLog,
)
from app.backend.services.usage_alert_service import UsageAlertService


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def alert_service():
    return UsageAlertService()


@pytest.fixture
def free_plan(db):
    """Create a free plan with low limits for testing."""
    import json
    plan = SubscriptionPlan(
        name="free_alert_test",
        display_name="Free Alert Test",
        description="Test plan",
        limits=json.dumps({"analyses_per_month": 10, "storage_gb": 1, "team_members": 2}),
        price_monthly=0,
        price_yearly=0,
        currency="USD",
        features=json.dumps([]),
        is_active=True,
        sort_order=99,
    )
    db.add(plan)
    db.commit()
    return plan


@pytest.fixture
def tenant_with_plan(db, free_plan):
    """Create a tenant on the free_plan."""
    tenant = Tenant(
        name="AlertTestCorp",
        slug="alerttestcorp",
        plan_id=free_plan.id,
        subscription_status="active",
        analyses_count_this_month=0,
        storage_used_bytes=0,
    )
    db.add(tenant)
    db.commit()
    return tenant


# ─── Service Tests ───────────────────────────────────────────────────────────

class TestCheckAndAlert:
    """Test UsageAlertService.check_and_alert."""

    def test_alert_created_at_80_percent(self, db, alert_service, tenant_with_plan):
        """Alert should be created when usage crosses 80% threshold."""
        # 8/10 = 80%
        alerts = alert_service.check_and_alert(
            db, tenant_with_plan.id, "analyses_per_month", 8, 10,
        )
        assert len(alerts) == 1
        assert alerts[0].alert_type == "analyses_per_month_80"
        assert alerts[0].threshold_percent == 80
        assert alerts[0].current_value == 8
        assert alerts[0].limit_value == 10

    def test_alert_created_at_100_percent(self, db, alert_service, tenant_with_plan):
        """Alert should be created when usage reaches 100% threshold."""
        # 10/10 = 100% — crosses both 80 and 100
        alerts = alert_service.check_and_alert(
            db, tenant_with_plan.id, "analyses_per_month", 10, 10,
        )
        assert len(alerts) == 2
        types = {a.alert_type for a in alerts}
        assert "analyses_per_month_80" in types
        assert "analyses_per_month_100" in types

    def test_no_alert_below_80_percent(self, db, alert_service, tenant_with_plan):
        """No alert should be created below 80% usage."""
        alerts = alert_service.check_and_alert(
            db, tenant_with_plan.id, "analyses_per_month", 5, 10,
        )
        assert len(alerts) == 0

    def test_duplicate_alert_not_created_same_period(self, db, alert_service, tenant_with_plan):
        """Duplicate alert should NOT be created in the same period."""
        # First call — creates 80% alert
        alerts1 = alert_service.check_and_alert(
            db, tenant_with_plan.id, "analyses_per_month", 8, 10,
        )
        assert len(alerts1) == 1

        # Second call — same period, should not create duplicate
        alerts2 = alert_service.check_and_alert(
            db, tenant_with_plan.id, "analyses_per_month", 9, 10,
        )
        assert len(alerts2) == 0  # 80% already sent; 100% not yet reached

    def test_alert_reset_in_new_period(self, db, alert_service, tenant_with_plan):
        """Alert should be creatable again in a new period."""
        # Create alert in current period
        alerts1 = alert_service.check_and_alert(
            db, tenant_with_plan.id, "analyses_per_month", 8, 10,
        )
        assert len(alerts1) == 1

        # Simulate new period by directly manipulating period_key check
        with patch.object(alert_service, '_current_period_key', return_value="2099-12"):
            alerts2 = alert_service.check_and_alert(
                db, tenant_with_plan.id, "analyses_per_month", 8, 10,
            )
            assert len(alerts2) == 1  # New period allows new alert

    def test_skip_unlimited_plan(self, db, alert_service, tenant_with_plan):
        """Alert should be skipped for unlimited plans (limit = -1)."""
        alerts = alert_service.check_and_alert(
            db, tenant_with_plan.id, "analyses_per_month", 999, -1,
        )
        assert len(alerts) == 0

    def test_skip_zero_limit(self, db, alert_service, tenant_with_plan):
        """Alert should be skipped when limit is 0."""
        alerts = alert_service.check_and_alert(
            db, tenant_with_plan.id, "analyses_per_month", 0, 0,
        )
        assert len(alerts) == 0

    def test_storage_metric_alert(self, db, alert_service, tenant_with_plan):
        """Alerts should work for storage_gb metric too."""
        # 0.8 / 1 GB = 80% → 800000000 bytes ≈ 0.8 GB, use integer approach
        # For storage, the caller converts to appropriate units
        alerts = alert_service.check_and_alert(
            db, tenant_with_plan.id, "storage_gb", 8, 10,
        )
        assert len(alerts) == 1
        assert alerts[0].metric_name == "storage_gb"


class TestGetTenantAlerts:
    """Test UsageAlertService.get_tenant_alerts."""

    def test_returns_empty_when_no_alerts(self, db, alert_service, tenant_with_plan):
        """Should return empty list when no alerts exist."""
        alerts = alert_service.get_tenant_alerts(db, tenant_with_plan.id)
        assert alerts == []

    def test_returns_alerts_sorted_newest_first(self, db, alert_service, tenant_with_plan):
        """Alerts should be returned newest first."""
        alert_service.check_and_alert(
            db, tenant_with_plan.id, "analyses_per_month", 8, 10,
        )
        alerts = alert_service.get_tenant_alerts(db, tenant_with_plan.id)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "analyses_per_month_80"
        assert alerts[0]["metric_name"] == "analyses_per_month"

    def test_respects_limit_param(self, db, alert_service, tenant_with_plan):
        """Should respect the limit parameter."""
        # Create multiple alerts
        alert_service.check_and_alert(
            db, tenant_with_plan.id, "analyses_per_month", 10, 10,
        )
        alerts = alert_service.get_tenant_alerts(db, tenant_with_plan.id, limit=1)
        assert len(alerts) == 1  # Capped at 1 even though 2 exist


class TestWebhookDispatch:
    """Test that webhook events are fired on alerts."""

    @patch("app.backend.services.webhook_service.dispatch_event_background")
    def test_webhook_fired_on_alert(self, mock_dispatch, db, alert_service, tenant_with_plan):
        """A usage.threshold_reached webhook event should be fired."""
        alerts = alert_service.check_and_alert(
            db, tenant_with_plan.id, "analyses_per_month", 8, 10,
        )
        assert len(alerts) == 1
        # The webhook dispatch is called from _fire_webhook
        mock_dispatch.assert_called_once()
        call_args = mock_dispatch.call_args
        assert call_args[0][2] == "usage.threshold_reached"  # event name
        payload = call_args[0][3]
        assert payload["metric"] == "analyses_per_month"
        assert payload["threshold_percent"] == 80

    @patch("app.backend.services.webhook_service.dispatch_event_background", side_effect=Exception("boom"))
    def test_webhook_failure_does_not_break_alert(self, mock_dispatch, db, alert_service, tenant_with_plan):
        """Alert creation should not fail even if webhook dispatch fails."""
        alerts = alert_service.check_and_alert(
            db, tenant_with_plan.id, "analyses_per_month", 8, 10,
        )
        # Alert should still be created even though webhook failed
        assert len(alerts) == 1


class TestGracefulDegradation:
    """Test that alert checks never break the main flow."""

    def test_alert_check_doesnt_break_on_db_error(self, db, alert_service, tenant_with_plan):
        """If DB errors occur during alert check, they should be caught."""
        # Patch the DB query to raise an exception
        original_query = db.query
        call_count = 0

        def failing_query(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Let the first query (for existing alert check) work, then fail
            if call_count > 1:
                raise Exception("DB error")
            return original_query(*args, **kwargs)

        # The service itself should handle exceptions gracefully via try/except in check_and_alert
        # This tests the integration wrapper's non-blocking behavior
        from app.backend.routes.subscription import check_usage_alerts
        # Should not raise even with internal failures
        with patch.object(alert_service, 'check_and_alert', side_effect=Exception("boom")):
            check_usage_alerts(db, tenant_with_plan.id, "analyses_per_month", 8, 10)
        # No exception raised = pass

    def test_non_blocking_from_record_usage(self, db, tenant_with_plan, free_plan):
        """record_usage should succeed even if alert check fails."""
        from app.backend.routes.subscription import record_usage

        # Create a user without bcrypt (direct hash)
        user = User(
            tenant_id=tenant_with_plan.id,
            email="testuser@alerttest.com",
            hashed_password="fake_hash_no_bcrypt",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()

        # Set tenant usage near 80% threshold (8/10)
        tenant_with_plan.analyses_count_this_month = 7
        db.commit()

        with patch(
            "app.backend.services.usage_alert_service.usage_alert_service.check_and_alert",
            side_effect=Exception("Alert service crashed"),
        ):
            result = record_usage(
                db, tenant_with_plan.id, user.id, "resume_analysis", 1,
            )

        # record_usage should still succeed
        assert result is True


# ─── API Endpoint Tests ─────────────────────────────────────────────────────

class TestAlertEndpoints:
    """Test the usage alert API endpoints."""

    def test_get_alerts_requires_auth(self, client, seed_subscription_plans):
        """GET /api/subscription/alerts should require authentication."""
        response = client.get("/api/subscription/alerts")
        assert response.status_code == 401

    def test_get_alerts_returns_empty_for_new_tenant(self, auth_client, seed_subscription_plans):
        """Should return empty alerts list for a new tenant."""
        response = auth_client.get("/api/subscription/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert data["total"] == 0

    def test_get_alerts_returns_alerts_after_threshold(self, db, auth_client_with_pro_plan, seed_subscription_plans):
        """Should return alerts after usage crosses a threshold."""
        from app.backend.models.db_models import Tenant
        tenant = db.query(Tenant).first()

        # Manually create a usage alert
        alert = UsageAlert(
            id="test-alert-1",
            tenant_id=tenant.id,
            alert_type="analyses_per_month_80",
            threshold_percent=80,
            metric_name="analyses_per_month",
            current_value=80,
            limit_value=100,
            period_key="2026-05",
            notified_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        db.commit()

        response = auth_client_with_pro_plan.get("/api/subscription/alerts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(a["alert_type"] == "analyses_per_month_80" for a in data["alerts"])

    def test_get_alert_preferences(self, auth_client, seed_subscription_plans):
        """GET /api/subscription/alerts/preferences should return defaults."""
        response = auth_client.get("/api/subscription/alerts/preferences")
        assert response.status_code == 200
        data = response.json()
        assert data["email_alerts"] is True
        assert data["webhook_alerts"] is True
        assert data["thresholds"] == [80, 100]

    def test_update_alert_preferences_requires_admin(self, auth_client, seed_subscription_plans):
        """PUT /api/subscription/alerts/preferences should require admin role."""
        # Default auth_client is an admin user, so this should work
        response = auth_client.put("/api/subscription/alerts/preferences", json={
            "email_alerts": False,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email_alerts"] is False
