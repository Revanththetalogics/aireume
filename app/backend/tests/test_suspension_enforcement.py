"""
Tests for subscription suspension enforcement across protected write endpoints.

Verifies that:
- Suspended/cancelled tenants are blocked from write operations (403)
- Read-only access is preserved for viewing existing data
- Billing/subscription routes remain accessible
- Past-due tenants get a warning header but are not blocked
- Reactivated tenants regain full access
"""
import pytest

from app.backend.models.db_models import Tenant, User


class TestSuspensionEnforcement:
    """End-to-end tests for subscription suspension middleware."""

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _get_auth_tenant(self, db):
        """Fetch the tenant created by the auth_client fixture."""
        user = db.query(User).filter(User.email == "admin@testcorp.com").first()
        assert user is not None, "Auth user not found in DB"
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        assert tenant is not None, "Auth tenant not found in DB"
        return tenant

    def _set_tenant_status(self, db, status: str):
        """Update the auth tenant's subscription_status."""
        tenant = self._get_auth_tenant(db)
        tenant.subscription_status = status
        db.commit()
        db.refresh(tenant)
        return tenant

    # ─── Suspended tenant blocked from write ──────────────────────────────────

    def test_suspended_tenant_cannot_submit_analysis(self, auth_client, db):
        """Suspended tenant gets 403 on any write endpoint."""
        self._set_tenant_status(db, "suspended")

        resp = auth_client.post(
            "/api/analyze/suggest-weights",
            data={"job_description": "Senior Python engineer with 5+ years experience in Django, FastAPI, AWS, and PostgreSQL. Must have strong API design skills."},
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["detail"]["error_code"] == "SUBSCRIPTION_SUSPENDED"
        assert data["detail"]["subscription_status"] == "suspended"

    # ─── Suspended tenant read-only grace period ──────────────────────────────

    def test_suspended_tenant_can_view_existing_results(self, auth_client, db):
        """Suspended tenant can still GET existing data."""
        self._set_tenant_status(db, "suspended")

        resp = auth_client.get("/api/history")
        assert resp.status_code == 200

    def test_suspended_tenant_can_access_billing_endpoints(self, auth_client, db):
        """Suspended tenant can still access billing routes to update payment."""
        self._set_tenant_status(db, "suspended")

        resp = auth_client.get("/api/billing/invoices")
        # Should return 200 (empty list if no invoices) even when suspended
        assert resp.status_code == 200

    # ─── Past-due tenant warning header ───────────────────────────────────────

    def test_past_due_tenant_can_submit_with_warning_header(self, auth_client, db):
        """Past-due tenant is not blocked but receives a warning header."""
        self._set_tenant_status(db, "past_due")

        resp = auth_client.post(
            "/api/analyze/suggest-weights",
            data={"job_description": "Senior Python engineer with 5+ years experience in Django, FastAPI, AWS, and PostgreSQL. Must have strong API design skills."},
        )
        assert resp.status_code == 200
        assert resp.headers.get("X-Subscription-Warning") == "past_due"

    # ─── Active tenant normal operation ───────────────────────────────────────

    def test_active_tenant_works_normally(self, auth_client, db):
        """Active tenant can submit analysis without any restriction."""
        tenant = self._get_auth_tenant(db)
        assert tenant.subscription_status == "active"

        resp = auth_client.post(
            "/api/analyze/suggest-weights",
            data={"job_description": "Senior Python engineer with 5+ years experience in Django, FastAPI, AWS, and PostgreSQL. Must have strong API design skills."},
        )
        assert resp.status_code == 200
        assert "X-Subscription-Warning" not in resp.headers

    # ─── Reactivation restores access ─────────────────────────────────────────

    def test_reactivated_tenant_regains_access(self, auth_client, db):
        """After reactivation, tenant can write again."""
        self._set_tenant_status(db, "suspended")

        # Verify blocked
        resp = auth_client.post(
            "/api/analyze/suggest-weights",
            data={"job_description": "Senior Python engineer with 5+ years experience in Django, FastAPI, AWS, and PostgreSQL. Must have strong API design skills."},
        )
        assert resp.status_code == 403

        # Reactivate
        self._set_tenant_status(db, "active")

        # Verify restored
        resp = auth_client.post(
            "/api/analyze/suggest-weights",
            data={"job_description": "Senior Python engineer with 5+ years experience in Django, FastAPI, AWS, and PostgreSQL. Must have strong API design skills."},
        )
        assert resp.status_code == 200

    # ─── Cancelled tenant also blocked ────────────────────────────────────────

    def test_cancelled_tenant_blocked_from_write(self, auth_client, db):
        """Cancelled subscription is also blocked from write operations."""
        self._set_tenant_status(db, "cancelled")

        resp = auth_client.post(
            "/api/analyze/suggest-weights",
            data={"job_description": "Senior Python engineer with 5+ years experience in Django, FastAPI, AWS, and PostgreSQL. Must have strong API design skills."},
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["detail"]["error_code"] == "SUBSCRIPTION_SUSPENDED"
        assert data["detail"]["subscription_status"] == "cancelled"
