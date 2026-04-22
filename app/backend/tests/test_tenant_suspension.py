"""
Tests for tenant suspension enforcement in auth middleware.
"""
import pytest
from datetime import datetime, timezone

from app.backend.models.db_models import Tenant, User


def test_unsuspended_tenant_works_normally(auth_client):
    """Normal auth works when tenant is not suspended."""
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == "admin@testcorp.com"


def test_suspended_tenant_gets_403(auth_client, db):
    """User of suspended tenant gets 403 with 'Account suspended' message."""
    # Suspend the tenant
    tenant = db.query(Tenant).filter(Tenant.slug == "testcorp").first()
    assert tenant is not None
    tenant.suspended_at = datetime.now(timezone.utc)
    tenant.suspended_reason = "Payment overdue"
    db.commit()

    # Try to access a protected endpoint
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 403
    assert "Account suspended" in resp.json()["detail"]


def test_platform_admin_bypasses_suspension(platform_admin_client, db):
    """Platform admin can still access API even if their tenant is suspended."""
    # Suspend the tenant
    tenant = db.query(Tenant).filter(Tenant.slug == "platformadmincorp").first()
    assert tenant is not None
    tenant.suspended_at = datetime.now(timezone.utc)
    db.commit()

    # Platform admin should still be able to access protected endpoints
    resp = platform_admin_client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == "platformadmin@test.com"


def test_public_routes_unaffected(client):
    """Login, register, health endpoints work regardless of suspension."""
    # Health endpoint should work without auth
    resp = client.get("/health")
    assert resp.status_code == 200

    # Register should work without auth
    resp = client.post("/api/auth/register", json={
        "company_name": "PublicRouteCorp",
        "email": "public@publicroutecorp.com",
        "password": "PublicPass123!",
        "full_name": "Public User",
    })
    assert resp.status_code in (200, 201)

    # Login should work without auth
    resp = client.post("/api/auth/login", json={
        "email": "public@publicroutecorp.com",
        "password": "PublicPass123!",
    })
    assert resp.status_code == 200


def test_suspend_then_reactivate(auth_client, db):
    """Setting suspended_at to None restores access."""
    tenant = db.query(Tenant).filter(Tenant.slug == "testcorp").first()
    assert tenant is not None

    # Suspend the tenant
    tenant.suspended_at = datetime.now(timezone.utc)
    db.commit()

    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 403
    assert "Account suspended" in resp.json()["detail"]

    # Reactivate the tenant
    tenant.suspended_at = None
    tenant.suspended_reason = None
    db.commit()

    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == "admin@testcorp.com"
