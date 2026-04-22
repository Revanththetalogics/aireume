"""
Phase 1 Regression Tests — verify existing functionality is intact after admin system additions.

These tests exercise the core user-facing flows to ensure no regressions
were introduced by Phase 1 admin management system (Tasks 1-7).
"""
import pytest


class TestAuthFlowRegression:
    """Verify the complete auth flow works unchanged."""

    def test_register_creates_tenant_and_user(self, client):
        """Registration still auto-creates tenant + admin user."""
        resp = client.post("/api/auth/register", json={
            "company_name": "RegressionCorp",
            "email": "regression@test.com",
            "password": "RegressionPass123!",
            "full_name": "Regression Tester",
        })
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "access_token" in data or "user" in data

    def test_login_returns_token(self, client):
        """Login flow still works."""
        # Register first
        client.post("/api/auth/register", json={
            "company_name": "LoginTestCorp",
            "email": "logintest@test.com",
            "password": "LoginTest123!",
            "full_name": "Login Tester",
        })
        # Login
        resp = client.post("/api/auth/login", json={
            "email": "logintest@test.com",
            "password": "LoginTest123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_me_endpoint_returns_user_and_tenant(self, auth_client):
        """GET /api/auth/me still returns user + tenant data."""
        resp = auth_client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data
        assert "tenant" in data


class TestSubscriptionFlowRegression:
    """Verify subscription system works unchanged."""

    def test_get_plans(self, client, seed_subscription_plans):
        """Public plans endpoint still returns all plans."""
        resp = client.get("/api/subscription/plans")
        assert resp.status_code == 200
        plans = resp.json()
        assert len(plans) >= 3

    def test_get_subscription_status(self, auth_client_with_free_plan):
        """Authenticated user can still check subscription status."""
        resp = auth_client_with_free_plan.get("/api/subscription")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_plan" in data
        assert "usage" in data

    def test_check_usage_allowed(self, auth_client_with_free_plan):
        """Usage check still works for users under limit."""
        resp = auth_client_with_free_plan.get("/api/subscription/check/resume_analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert "allowed" in data

    def test_admin_reset_usage(self, auth_client_with_free_plan):
        """Tenant admin can still reset usage via existing endpoint."""
        resp = auth_client_with_free_plan.post("/api/subscription/admin/reset-usage")
        assert resp.status_code == 200


class TestTeamManagementRegression:
    """Verify team management works unchanged."""

    def test_list_team_members(self, auth_client):
        """Team list endpoint still works."""
        resp = auth_client.get("/api/team")
        assert resp.status_code == 200

    def test_invite_team_member(self, auth_client):
        """Team invite still works for admin users."""
        resp = auth_client.post("/api/invites", json={
            "email": "newmember@testcorp.com",
            "role": "recruiter",
            "full_name": "New Member",
        })
        assert resp.status_code in (200, 201)


class TestHealthEndpointsRegression:
    """Verify health/diagnostic endpoints still work."""

    def test_health_check(self, client):
        """Shallow health check still responds."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_root_endpoint(self, client):
        """Root endpoint still returns version info."""
        resp = client.get("/")
        assert resp.status_code == 200


class TestNewAdminEndpointsAccessControl:
    """Verify new admin endpoints are properly secured."""

    def test_regular_user_cannot_access_admin_tenants(self, auth_client):
        """Regular tenant admin (not platform admin) gets 403 on admin routes."""
        resp = auth_client.get("/api/admin/tenants")
        assert resp.status_code == 403

    def test_unauthenticated_cannot_access_admin(self, client):
        """Unauthenticated user gets 401 on admin routes."""
        resp = client.get("/api/admin/tenants")
        assert resp.status_code == 401

    def test_platform_admin_can_access_admin_tenants(self, platform_admin_client):
        """Platform admin can access admin routes."""
        resp = platform_admin_client.get("/api/admin/tenants")
        assert resp.status_code == 200
