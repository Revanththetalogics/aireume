"""
Tests for subscription plan CRUD admin endpoints.
"""
import json
import pytest
from app.backend.models.db_models import Tenant, User, SubscriptionPlan, AuditLog


# ─── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def billing_admin_client(client, db):
    """Returns a TestClient with a billing_admin platform role."""
    register_payload = {
        "company_name": "BillingAdminCorp",
        "email": "billingadmin@test.com",
        "password": "BillingAdmin123!",
        "full_name": "Billing Admin",
    }
    reg_resp = client.post("/api/auth/register", json=register_payload)
    assert reg_resp.status_code in (200, 201), f"Register failed: {reg_resp.text}"

    login_resp = client.post("/api/auth/login", json={
        "email": "billingadmin@test.com",
        "password": "BillingAdmin123!",
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]

    user = db.query(User).filter(User.email == "billingadmin@test.com").first()
    user.is_platform_admin = False
    user.platform_role = "billing_admin"
    db.commit()

    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture(scope="function")
def super_admin_client(client, db):
    """Returns a TestClient with an explicit super_admin platform role."""
    register_payload = {
        "company_name": "SuperAdminCorp",
        "email": "superadmin@test.com",
        "password": "SuperAdmin123!",
        "full_name": "Super Admin",
    }
    reg_resp = client.post("/api/auth/register", json=register_payload)
    assert reg_resp.status_code in (200, 201), f"Register failed: {reg_resp.text}"

    login_resp = client.post("/api/auth/login", json={
        "email": "superadmin@test.com",
        "password": "SuperAdmin123!",
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]

    user = db.query(User).filter(User.email == "superadmin@test.com").first()
    user.is_platform_admin = False
    user.platform_role = "super_admin"
    db.commit()

    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ─── List Plans ─────────────────────────────────────────────────────────────────

class TestListPlans:

    def test_list_plans_requires_billing_admin(self, auth_client, seed_subscription_plans):
        """Regular users get 403."""
        resp = auth_client.get("/api/admin/plans")
        assert resp.status_code == 403

    def test_list_plans_billing_admin(self, billing_admin_client, seed_subscription_plans):
        """Billing admin can list all plans including subscriber counts."""
        resp = billing_admin_client.get("/api/admin/plans")
        assert resp.status_code == 200
        data = resp.json()
        assert "plans" in data
        assert "total" in data
        assert data["total"] >= 3
        for plan in data["plans"]:
            assert "subscriber_count" in plan
            assert "id" in plan
            assert "name" in plan
            assert "is_active" in plan

    def test_list_plans_super_admin(self, super_admin_client, seed_subscription_plans):
        """Super admin can list all plans."""
        resp = super_admin_client.get("/api/admin/plans")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3

    def test_list_plans_includes_inactive(self, super_admin_client, db, seed_subscription_plans):
        """Inactive plans are included in the list."""
        plan = SubscriptionPlan(
            name="inactive_plan",
            display_name="Inactive Plan",
            price_monthly=0,
            price_yearly=0,
            limits="{}",
            features="[]",
            is_active=False,
            sort_order=99,
        )
        db.add(plan)
        db.commit()

        resp = super_admin_client.get("/api/admin/plans")
        assert resp.status_code == 200
        data = resp.json()
        names = {p["name"] for p in data["plans"]}
        assert "inactive_plan" in names

    def test_list_plans_subscriber_count(self, super_admin_client, db, seed_subscription_plans, client):
        """Subscriber count reflects active tenants on the plan."""
        free_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "free").first()

        # Create a tenant on the free plan
        reg = client.post("/api/auth/register", json={
            "company_name": "SubCorp",
            "email": "sub@subcorp.com",
            "password": "SubPass123!",
            "full_name": "Sub User",
        })
        assert reg.status_code in (200, 201)
        tenant = db.query(Tenant).filter(Tenant.slug == "subcorp").first()
        tenant.plan_id = free_plan.id
        tenant.subscription_status = "active"
        db.commit()

        resp = super_admin_client.get("/api/admin/plans")
        assert resp.status_code == 200
        for plan in resp.json()["plans"]:
            if plan["name"] == "free":
                assert plan["subscriber_count"] >= 1


# ─── Create Plan ────────────────────────────────────────────────────────────────

class TestCreatePlan:

    def test_create_plan_success(self, billing_admin_client, db):
        """Create a new plan with all fields."""
        payload = {
            "name": "starter",
            "display_name": "Starter",
            "description": "Starter tier",
            "price_monthly": 999,
            "price_yearly": 9999,
            "currency": "usd",
            "limits": {"analyses_per_month": 50, "team_members": 3, "storage_gb": 5, "batch_size": 10},
            "features": ["50 analyses", "3 team members"],
            "is_active": True,
            "sort_order": 5,
        }
        resp = billing_admin_client.post("/api/admin/plans", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "starter"
        assert data["display_name"] == "Starter"
        assert data["price_monthly"] == 999
        assert data["price_yearly"] == 9999
        assert data["currency"] == "USD"
        assert data["limits"]["analyses_per_month"] == 50
        assert data["features"] == ["50 analyses", "3 team members"]
        assert data["is_active"] is True
        assert data["sort_order"] == 5

        # Audit log
        audit = db.query(AuditLog).filter(
            AuditLog.action == "plan.create",
            AuditLog.resource_id == data["id"],
        ).first()
        assert audit is not None

    def test_create_plan_defaults(self, billing_admin_client):
        """Create with minimal required fields."""
        payload = {
            "name": "minimal",
            "display_name": "Minimal",
            "price_monthly": 0,
            "price_yearly": 0,
        }
        resp = billing_admin_client.post("/api/admin/plans", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["is_active"] is True
        assert data["currency"] == "USD"
        assert data["limits"] == {}
        assert data["features"] == []
        assert data["sort_order"] == 0

    def test_create_plan_duplicate_name(self, billing_admin_client, seed_subscription_plans):
        """Name uniqueness is enforced."""
        payload = {
            "name": "free",
            "display_name": "Free Duplicate",
            "price_monthly": 0,
            "price_yearly": 0,
        }
        resp = billing_admin_client.post("/api/admin/plans", json=payload)
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_create_plan_negative_price(self, billing_admin_client):
        """Price must be >= 0."""
        payload = {
            "name": "bad_price",
            "display_name": "Bad Price",
            "price_monthly": -1,
            "price_yearly": 0,
        }
        resp = billing_admin_client.post("/api/admin/plans", json=payload)
        assert resp.status_code == 400
        assert "price_monthly" in resp.json()["detail"]

    def test_create_plan_invalid_limits_type(self, billing_admin_client):
        """Limits must be an object with integer values."""
        payload = {
            "name": "bad_limits",
            "display_name": "Bad Limits",
            "price_monthly": 0,
            "price_yearly": 0,
            "limits": {"analyses_per_month": "unlimited"},
        }
        resp = billing_admin_client.post("/api/admin/plans", json=payload)
        assert resp.status_code == 400
        assert "integer" in resp.json()["detail"].lower()

    def test_create_plan_requires_auth(self, client):
        """Unauthenticated requests are blocked (403 from CSRF middleware for POST)."""
        resp = client.post("/api/admin/plans", json={
            "name": "noauth",
            "display_name": "No Auth",
            "price_monthly": 0,
            "price_yearly": 0,
        })
        assert resp.status_code == 403


# ─── Update Plan ────────────────────────────────────────────────────────────────

class TestUpdatePlan:

    def test_update_plan_success(self, billing_admin_client, db, seed_subscription_plans):
        """Partial update works."""
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "free").first()
        resp = billing_admin_client.put(f"/api/admin/plans/{plan.id}", json={
            "display_name": "Free Updated",
            "price_monthly": 100,
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["display_name"] == "Free Updated"
        assert data["price_monthly"] == 100
        # Unchanged fields preserved
        assert data["name"] == "free"

        # Audit log with diff
        audit = db.query(AuditLog).filter(
            AuditLog.action == "plan.update",
            AuditLog.resource_id == plan.id,
        ).order_by(AuditLog.created_at.desc()).first()
        assert audit is not None
        details = json.loads(audit.details)
        assert "before" in details
        assert "after" in details
        assert details["after"]["display_name"] == "Free Updated"

    def test_update_plan_name_uniqueness(self, billing_admin_client, db, seed_subscription_plans):
        """Renaming to an existing name fails."""
        free_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "free").first()
        resp = billing_admin_client.put(f"/api/admin/plans/{free_plan.id}", json={
            "name": "pro",
        })
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_update_plan_not_found(self, billing_admin_client):
        """Updating non-existent plan returns 404."""
        resp = billing_admin_client.put("/api/admin/plans/99999", json={
            "display_name": "Ghost",
        })
        assert resp.status_code == 404

    def test_update_plan_limits(self, billing_admin_client, db, seed_subscription_plans):
        """Update limits field."""
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "free").first()
        resp = billing_admin_client.put(f"/api/admin/plans/{plan.id}", json={
            "limits": {"analyses_per_month": 10, "team_members": 2, "storage_gb": 2, "batch_size": 5},
        })
        assert resp.status_code == 200
        assert resp.json()["limits"]["analyses_per_month"] == 10

    def test_update_plan_features(self, billing_admin_client, db, seed_subscription_plans):
        """Update features field."""
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "free").first()
        resp = billing_admin_client.put(f"/api/admin/plans/{plan.id}", json={
            "features": ["new feature"],
        })
        assert resp.status_code == 200
        assert resp.json()["features"] == ["new feature"]

    def test_update_plan_currency_uppercase(self, billing_admin_client, db, seed_subscription_plans):
        """Currency is normalized to uppercase."""
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "free").first()
        resp = billing_admin_client.put(f"/api/admin/plans/{plan.id}", json={
            "currency": "eur",
        })
        assert resp.status_code == 200
        assert resp.json()["currency"] == "EUR"


# ─── Archive Plan ───────────────────────────────────────────────────────────────

class TestArchivePlan:

    def test_archive_plan_success(self, super_admin_client, db, seed_subscription_plans):
        """Super admin can archive a plan with no subscribers."""
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "enterprise").first()
        resp = super_admin_client.delete(f"/api/admin/plans/{plan.id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["message"] == "Plan archived successfully"
        assert data["plan_id"] == plan.id

        db.refresh(plan)
        assert plan.is_active is False

        # Audit log
        audit = db.query(AuditLog).filter(
            AuditLog.action == "plan.archive",
            AuditLog.resource_id == plan.id,
        ).first()
        assert audit is not None

    def test_archive_plan_conflict_with_subscribers(self, super_admin_client, db, seed_subscription_plans, client):
        """Archiving a plan with active subscribers returns 409."""
        pro_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "pro").first()

        # Create tenant on pro plan
        reg = client.post("/api/auth/register", json={
            "company_name": "ProSubCorp",
            "email": "prosub@prosubcorp.com",
            "password": "ProSub123!",
            "full_name": "Pro Sub",
        })
        assert reg.status_code in (200, 201)
        tenant = db.query(Tenant).filter(Tenant.slug == "prosubcorp").first()
        tenant.plan_id = pro_plan.id
        tenant.subscription_status = "active"
        db.commit()

        resp = super_admin_client.delete(f"/api/admin/plans/{pro_plan.id}")
        assert resp.status_code == 409
        assert "active subscriber" in resp.json()["detail"]
        assert "force=true" in resp.json()["detail"]

    def test_archive_plan_force(self, super_admin_client, db, seed_subscription_plans, client):
        """Force archive bypasses subscriber check."""
        pro_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "pro").first()

        # Create tenant on pro plan
        reg = client.post("/api/auth/register", json={
            "company_name": "ForceCorp",
            "email": "force@forcecorp.com",
            "password": "Force123!",
            "full_name": "Force User",
        })
        assert reg.status_code in (200, 201)
        tenant = db.query(Tenant).filter(Tenant.slug == "forcecorp").first()
        tenant.plan_id = pro_plan.id
        tenant.subscription_status = "active"
        db.commit()

        resp = super_admin_client.delete(f"/api/admin/plans/{pro_plan.id}?force=true")
        assert resp.status_code == 200
        db.refresh(pro_plan)
        assert pro_plan.is_active is False

    def test_archive_plan_not_found(self, super_admin_client):
        """Archiving non-existent plan returns 404."""
        resp = super_admin_client.delete("/api/admin/plans/99999")
        assert resp.status_code == 404

    def test_archive_plan_already_archived(self, super_admin_client, db, seed_subscription_plans):
        """Archiving an already archived plan returns 400."""
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "enterprise").first()
        plan.is_active = False
        db.commit()

        resp = super_admin_client.delete(f"/api/admin/plans/{plan.id}")
        assert resp.status_code == 400
        assert "already archived" in resp.json()["detail"]

    def test_archive_plan_billing_admin_forbidden(self, billing_admin_client, db, seed_subscription_plans):
        """Billing admin cannot archive plans."""
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "enterprise").first()
        resp = billing_admin_client.delete(f"/api/admin/plans/{plan.id}")
        assert resp.status_code == 403


# ─── Role Checks ────────────────────────────────────────────────────────────────

class TestRoleChecks:

    def test_billing_admin_can_create(self, billing_admin_client):
        """Billing admin can create plans."""
        resp = billing_admin_client.post("/api/admin/plans", json={
            "name": "billing_test",
            "display_name": "Billing Test",
            "price_monthly": 0,
            "price_yearly": 0,
        })
        assert resp.status_code == 201

    def test_billing_admin_can_update(self, billing_admin_client, db, seed_subscription_plans):
        """Billing admin can update plans."""
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "free").first()
        resp = billing_admin_client.put(f"/api/admin/plans/{plan.id}", json={
            "display_name": "Updated by Billing",
        })
        assert resp.status_code == 200

    def test_super_admin_can_create(self, super_admin_client):
        """Super admin can create plans."""
        resp = super_admin_client.post("/api/admin/plans", json={
            "name": "super_test",
            "display_name": "Super Test",
            "price_monthly": 0,
            "price_yearly": 0,
        })
        assert resp.status_code == 201

    def test_regular_user_cannot_access(self, auth_client, seed_subscription_plans):
        """Regular user gets 403 on all plan admin endpoints."""
        endpoints = [
            ("get", "/api/admin/plans"),
            ("post", "/api/admin/plans"),
            ("put", "/api/admin/plans/1"),
            ("delete", "/api/admin/plans/1"),
        ]
        for method, url in endpoints:
            if method == "get":
                resp = auth_client.get(url)
            elif method == "post":
                resp = auth_client.post(url, json={
                    "name": "x", "display_name": "X", "price_monthly": 0, "price_yearly": 0,
                })
            elif method == "put":
                resp = auth_client.put(url, json={"display_name": "X"})
            else:
                resp = auth_client.delete(url)
            assert resp.status_code == 403, f"Expected 403 for {method.upper()} {url}, got {resp.status_code}"
