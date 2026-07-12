"""
Tests for onboarding API routes: status, organization, plan selection, completion.
"""
import pytest
import json
from app.backend.models.db_models import SubscriptionPlan, Tenant


# ─── Onboarding Status Tests ────────────────────────────────────────────────────

class TestGetOnboardingStatus:
    """Tests for GET /api/onboarding/status endpoint."""

    def test_status_requires_auth(self, client):
        """Should return 401 without authentication."""
        response = client.get("/api/onboarding/status")
        assert response.status_code == 401

    def test_status_returns_incomplete_for_new_tenant(self, auth_client):
        """New tenants should have onboarding_completed=False."""
        response = auth_client.get("/api/onboarding/status")
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is False
        assert data["completed_at"] is None
        assert "steps" in data
        assert "organization" in data["steps"]
        assert "plan_selected" in data["steps"]
        assert "first_jd" in data["steps"]

    def test_status_returns_complete_after_completion(self, auth_client, db):
        """After onboarding is marked complete, status should reflect that."""
        # Manually mark onboarding as complete
        tenant = db.query(Tenant).first()
        tenant.onboarding_completed = True
        from datetime import datetime, timezone
        tenant.onboarding_completed_at = datetime.now(timezone.utc)
        db.commit()

        response = auth_client.get("/api/onboarding/status")
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is True
        assert data["completed_at"] is not None


# ─── Update Organization Tests ──────────────────────────────────────────────────

class TestUpdateOrganization:
    """Tests for POST /api/onboarding/organization endpoint."""

    def test_organization_requires_auth(self, client):
        """Should return 401 or 403 without authentication."""
        response = client.post("/api/onboarding/organization", json={"name": "Test"})
        assert response.status_code in (401, 403)

    def test_update_organization_name(self, auth_client, db):
        """Should update tenant name."""
        response = auth_client.post("/api/onboarding/organization", json={
            "name": "New Org Name",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tenant"]["name"] == "New Org Name"

        # Verify in DB
        tenant = db.query(Tenant).first()
        assert tenant.name == "New Org Name"

    def test_update_organization_with_industry_and_size(self, auth_client, db):
        """Should update tenant name, industry, and company size in metadata."""
        response = auth_client.post("/api/onboarding/organization", json={
            "name": "TechCorp",
            "industry": "Technology",
            "company_size": "11-50",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify metadata was saved
        tenant = db.query(Tenant).first()
        metadata = json.loads(tenant.metadata_json)
        assert metadata["industry"] == "Technology"
        assert metadata["company_size"] == "11-50"

    def test_update_organization_strips_whitespace(self, auth_client, db):
        """Should strip whitespace from organization name."""
        response = auth_client.post("/api/onboarding/organization", json={
            "name": "  Spaced Corp  ",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["tenant"]["name"] == "Spaced Corp"

    def test_update_organization_optional_fields(self, auth_client, db):
        """Industry and company_size should be optional."""
        response = auth_client.post("/api/onboarding/organization", json={
            "name": "Minimal Corp",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_organization_step_reflected_in_status(self, auth_client, db):
        """After updating organization with industry, status should show step complete."""
        auth_client.post("/api/onboarding/organization", json={
            "name": "TestCorp",
            "industry": "Finance",
            "company_size": "1-10",
        })

        response = auth_client.get("/api/onboarding/status")
        data = response.json()
        assert data["steps"]["organization"] is True


# ─── Select Plan Tests ─────────────────────────────────────────────────────────

class TestSelectPlan:
    """Tests for POST /api/onboarding/select-plan endpoint."""

    def test_select_plan_requires_auth(self, client):
        """Should return 401 or 403 without authentication."""
        response = client.post("/api/onboarding/select-plan", json={"plan_id": 1})
        assert response.status_code in (401, 403)

    def test_select_valid_plan(self, auth_client, seed_subscription_plans, db):
        """Should set plan_id on tenant."""
        # Get the free plan id
        free_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name.in_(("starter", "free"))).first()

        response = auth_client.post("/api/onboarding/select-plan", json={
            "plan_id": free_plan.id,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["plan"]["name"] == "starter"

        # Verify tenant plan_id was updated
        tenant = db.query(Tenant).first()
        assert tenant.plan_id == free_plan.id

    def test_select_invalid_plan(self, auth_client, db):
        """Should return 400 for invalid plan_id."""
        response = auth_client.post("/api/onboarding/select-plan", json={
            "plan_id": 99999,
        })
        assert response.status_code == 400
        assert "Invalid or inactive" in response.json()["detail"]

    def test_select_inactive_plan(self, auth_client, db):
        """Should return 400 for inactive plan."""
        # Create an inactive plan
        inactive_plan = SubscriptionPlan(
            name="inactive_plan",
            display_name="Inactive",
            description="Not available",
            limits="{}",
            price_monthly=0,
            price_yearly=0,
            features="[]",
            is_active=False,
            sort_order=99,
        )
        db.add(inactive_plan)
        db.commit()
        db.refresh(inactive_plan)

        response = auth_client.post("/api/onboarding/select-plan", json={
            "plan_id": inactive_plan.id,
        })
        assert response.status_code == 400

    def test_plan_step_reflected_in_status(self, auth_client, seed_subscription_plans, db):
        """After selecting a plan, status should show plan_selected=True."""
        free_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name.in_(("starter", "free"))).first()

        auth_client.post("/api/onboarding/select-plan", json={"plan_id": free_plan.id})

        response = auth_client.get("/api/onboarding/status")
        data = response.json()
        assert data["steps"]["plan_selected"] is True


# ─── Complete Onboarding Tests ──────────────────────────────────────────────────

class TestCompleteOnboarding:
    """Tests for POST /api/onboarding/complete endpoint."""

    def test_complete_requires_auth(self, client):
        """Should return 401 or 403 without authentication."""
        response = client.post("/api/onboarding/complete")
        assert response.status_code in (401, 403)

    def test_complete_onboarding(self, auth_client, seed_subscription_plans, db):
        """Should mark onboarding as complete."""
        # Prerequisite: select a plan before completing
        free_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name.in_(("starter", "free"))).first()
        auth_client.post("/api/onboarding/select-plan", json={"plan_id": free_plan.id})

        response = auth_client.post("/api/onboarding/complete")
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is True
        assert data["redirect_to"] == "/"

        # Verify tenant state in DB
        tenant = db.query(Tenant).first()
        assert tenant.onboarding_completed is True
        assert tenant.onboarding_completed_at is not None

    def test_complete_onboarding_idempotent(self, auth_client, seed_subscription_plans, db):
        """Calling complete again should still succeed."""
        # Prerequisite: select a plan before completing
        free_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name.in_(("starter", "free"))).first()
        auth_client.post("/api/onboarding/select-plan", json={"plan_id": free_plan.id})

        auth_client.post("/api/onboarding/complete")

        response = auth_client.post("/api/onboarding/complete")
        assert response.status_code == 200
        data = response.json()
        assert data["already_completed"] is True

    def test_status_after_complete(self, auth_client, seed_subscription_plans, db):
        """Status endpoint should reflect completed onboarding."""
        # Prerequisite: select a plan before completing
        free_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name.in_(("starter", "free"))).first()
        auth_client.post("/api/onboarding/select-plan", json={"plan_id": free_plan.id})

        auth_client.post("/api/onboarding/complete")

        response = auth_client.get("/api/onboarding/status")
        data = response.json()
        assert data["completed"] is True
        assert data["completed_at"] is not None


# ─── Full Onboarding Flow Test ─────────────────────────────────────────────────

class TestOnboardingFlow:
    """Integration test for the complete onboarding flow."""

    def test_full_onboarding_flow(self, auth_client, seed_subscription_plans, db):
        """Test the complete onboarding flow: status -> org -> plan -> complete."""
        # 1. Check initial status
        response = auth_client.get("/api/onboarding/status")
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is False

        # 2. Update organization
        response = auth_client.post("/api/onboarding/organization", json={
            "name": "FlowCorp",
            "industry": "Technology",
            "company_size": "51-200",
        })
        assert response.status_code == 200

        # 3. Select plan
        free_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name.in_(("starter", "free"))).first()
        response = auth_client.post("/api/onboarding/select-plan", json={
            "plan_id": free_plan.id,
        })
        assert response.status_code == 200

        # 4. Complete onboarding
        response = auth_client.post("/api/onboarding/complete")
        assert response.status_code == 200
        assert response.json()["completed"] is True

        # 5. Verify final status
        response = auth_client.get("/api/onboarding/status")
        data = response.json()
        assert data["completed"] is True
        assert data["steps"]["organization"] is True
        assert data["steps"]["plan_selected"] is True


class TestSkipOnboarding:
    def test_skip_auto_selects_free_plan_and_completes(self, auth_client, seed_subscription_plans, db):
        response = auth_client.post("/api/onboarding/skip")
        assert response.status_code == 200
        assert response.json()["completed"] is True

        tenant = db.query(Tenant).first()
        assert tenant.onboarding_completed is True
        assert tenant.plan_id is not None


class TestInviteTeamOnboarding:
    def test_invite_team_sends_invites(self, auth_client, db):
        response = auth_client.post("/api/onboarding/invite-team", json={
            "emails": ["newhire@example.com"],
            "role": "recruiter",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["invited_count"] >= 0
        assert len(data["results"]) == 1
