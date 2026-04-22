"""
Tests for the email notification service and admin notification endpoints.
"""
import os
from unittest.mock import MagicMock, patch, call

import pytest

from app.backend.services.email_service import EmailService


# ─── Unit tests for EmailService ─────────────────────────────────────────────


class TestEmailServiceUnit:
    """Unit tests for the EmailService class."""

    def _make_configured_service(self):
        """Return an EmailService that appears fully configured."""
        svc = EmailService.__new__(EmailService)
        svc.smtp_host = "smtp.example.com"
        svc.smtp_port = 587
        svc.smtp_user = "user@example.com"
        svc.smtp_password = "secret"
        svc.smtp_from = "noreply@example.com"
        return svc

    def _make_unconfigured_service(self):
        """Return an EmailService with no SMTP settings."""
        svc = EmailService.__new__(EmailService)
        svc.smtp_host = None
        svc.smtp_port = 587
        svc.smtp_user = None
        svc.smtp_password = None
        svc.smtp_from = None
        return svc

    # ── is_configured ──────────────────────────────────────────────────────

    def test_is_configured_true(self):
        svc = self._make_configured_service()
        assert svc.is_configured is True

    def test_is_configured_false(self):
        svc = self._make_unconfigured_service()
        assert svc.is_configured is False

    # ── send_email ─────────────────────────────────────────────────────────

    def test_send_email_succeeds_with_mock_smtp(self):
        svc = self._make_configured_service()
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch("app.backend.services.email_service.smtplib.SMTP", return_value=mock_smtp):
            result = svc.send_email("admin@test.com", "Hello", "<b>Hi</b>")

        assert result is True
        mock_smtp.ehlo.assert_called_once()
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user@example.com", "secret")
        mock_smtp.sendmail.assert_called_once()

    def test_send_email_returns_false_when_not_configured(self):
        svc = self._make_unconfigured_service()
        result = svc.send_email("admin@test.com", "Hello", "<b>Hi</b>")
        assert result is False

    def test_send_email_returns_false_on_smtp_exception(self):
        svc = self._make_configured_service()
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)
        mock_smtp.sendmail.side_effect = Exception("connection refused")

        with patch("app.backend.services.email_service.smtplib.SMTP", return_value=mock_smtp):
            result = svc.send_email("admin@test.com", "Hello", "<b>Hi</b>")

        assert result is False

    # ── send_quota_warning ─────────────────────────────────────────────────

    def test_send_quota_warning_formats_correctly(self):
        svc = self._make_configured_service()
        with patch.object(svc, "send_email", return_value=True) as mock_send:
            result = svc.send_quota_warning("AcmeCorp", "admin@acme.com", 85)

        assert result is True
        mock_send.assert_called_once()
        args = mock_send.call_args
        assert args[1]["to"] == "admin@acme.com"
        assert "AcmeCorp" in args[1]["subject"]
        assert "85%" in args[1]["subject"]
        assert "AcmeCorp" in args[1]["body_html"]
        assert "85%" in args[1]["body_html"]

    # ── send_subscription_expiry ───────────────────────────────────────────

    def test_send_subscription_expiry_formats_correctly(self):
        svc = self._make_configured_service()
        with patch.object(svc, "send_email", return_value=True) as mock_send:
            result = svc.send_subscription_expiry("BetaInc", "admin@beta.com", 3)

        assert result is True
        args = mock_send.call_args
        assert args[1]["to"] == "admin@beta.com"
        assert "BetaInc" in args[1]["subject"]
        assert "3 days" in args[1]["subject"]
        assert "BetaInc" in args[1]["body_html"]
        assert "3 days" in args[1]["body_html"]

    # ── send_suspension_notice ─────────────────────────────────────────────

    def test_send_suspension_notice_formats_correctly(self):
        svc = self._make_configured_service()
        with patch.object(svc, "send_email", return_value=True) as mock_send:
            result = svc.send_suspension_notice(
                "GammaLLC", "admin@gamma.com", "Payment overdue"
            )

        assert result is True
        args = mock_send.call_args
        assert args[1]["to"] == "admin@gamma.com"
        assert "GammaLLC" in args[1]["subject"]
        assert "GammaLLC" in args[1]["body_html"]
        assert "Payment overdue" in args[1]["body_html"]

    def test_send_email_no_auth_when_credentials_missing(self):
        """When smtp_user/password are None, starttls/login should NOT be called."""
        svc = self._make_configured_service()
        svc.smtp_user = None
        svc.smtp_password = None
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch("app.backend.services.email_service.smtplib.SMTP", return_value=mock_smtp):
            result = svc.send_email("admin@test.com", "Hello", "<b>Hi</b>")

        assert result is True
        mock_smtp.starttls.assert_not_called()
        mock_smtp.login.assert_not_called()


# ─── Integration tests for admin notification endpoints ──────────────────────


@pytest.fixture
def configured_email_service():
    """Return a fully configured EmailService and patch the module singleton."""
    svc = EmailService.__new__(EmailService)
    svc.smtp_host = "smtp.test.com"
    svc.smtp_port = 587
    svc.smtp_user = "test@test.com"
    svc.smtp_password = "testpass"
    svc.smtp_from = "noreply@test.com"
    return svc


class TestAdminNotificationEndpoints:
    """Integration tests for /api/admin/notifications/* endpoints."""

    def test_get_config_returns_status(self, platform_admin_client, configured_email_service):
        with patch("app.backend.services.email_service.email_service", configured_email_service):
            resp = platform_admin_client.get("/api/admin/notifications/config")

        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is True
        assert data["smtp_host"] == "smtp.test.com"
        assert data["smtp_from"] == "noreply@test.com"
        # Password must never be exposed
        assert "smtp_password" not in data
        assert "password" not in data

    def test_get_config_unconfigured(self, platform_admin_client):
        unconfigured = EmailService.__new__(EmailService)
        unconfigured.smtp_host = None
        unconfigured.smtp_port = 587
        unconfigured.smtp_user = None
        unconfigured.smtp_password = None
        unconfigured.smtp_from = None

        with patch("app.backend.services.email_service.email_service", unconfigured):
            resp = platform_admin_client.get("/api/admin/notifications/config")

        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is False
        assert data["smtp_host"] is None
        assert data["smtp_from"] is None

    def test_post_test_email_sends_email(self, platform_admin_client, configured_email_service):
        with patch("app.backend.services.email_service.email_service", configured_email_service), \
             patch.object(configured_email_service, "send_email", return_value=True) as mock_send:
            resp = platform_admin_client.post(
                "/api/admin/notifications/test",
                json={"email": "custom@test.com"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "sent" in data["message"].lower()
        assert data["recipient"] == "custom@test.com"
        mock_send.assert_called_once()
        assert mock_send.call_args[1]["to"] == "custom@test.com"

    def test_post_test_email_uses_admin_email_when_not_provided(
        self, platform_admin_client, configured_email_service
    ):
        with patch("app.backend.services.email_service.email_service", configured_email_service), \
             patch.object(configured_email_service, "send_email", return_value=True) as mock_send:
            resp = platform_admin_client.post("/api/admin/notifications/test", json={})

        assert resp.status_code == 200
        data = resp.json()
        assert data["recipient"] == "platformadmin@test.com"
        assert mock_send.call_args[1]["to"] == "platformadmin@test.com"

    def test_non_admin_cannot_access_notification_config(self, auth_client):
        resp = auth_client.get("/api/admin/notifications/config")
        assert resp.status_code == 403

    def test_non_admin_cannot_send_test_email(self, auth_client):
        resp = auth_client.post("/api/admin/notifications/test", json={})
        assert resp.status_code == 403

    def test_unauthenticated_cannot_access_notifications(self, client):
        resp = client.get("/api/admin/notifications/config")
        assert resp.status_code in (401, 403)
