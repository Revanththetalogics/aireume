"""
Tests for feature flag service and admin endpoints.
"""
import pytest
from fastapi import HTTPException
from app.backend.models.db_models import FeatureFlag, TenantFeatureOverride, Tenant, User
from app.backend.services.feature_flag_service import (
    is_feature_enabled,
    invalidate_cache,
    get_all_flags,
    get_tenant_overrides,
)


@pytest.fixture(autouse=True)
def clear_feature_flag_cache():
    """Clear the feature flag cache before and after each test."""
    invalidate_cache()
    yield
    invalidate_cache()


@pytest.fixture
def seed_feature_flags(db):
    """Seed default feature flags for testing (matches migration 013)."""
    flags_data = [
        ("video_analysis", "Video Analysis"),
        ("batch_analysis", "Batch Analysis"),
        ("custom_weights", "Custom Scoring Weights"),
        ("api_access", "API Access"),
        ("export_excel", "Excel Export"),
        ("transcript_analysis", "Transcript Analysis"),
        ("email_generation", "Email Generation"),
    ]
    for key, display in flags_data:
        flag = FeatureFlag(key=key, display_name=display, enabled_globally=True)
        db.add(flag)
    db.commit()
    return flags_data


class TestIsFeatureEnabled:
    def test_is_feature_enabled_default_true(self, db):
        """Unknown flag returns True (safe default)."""
        assert is_feature_enabled(db, tenant_id=1, feature_key="nonexistent_flag") is True

    def test_is_feature_enabled_global_true(self, db, seed_feature_flags):
        """Existing flag enabled globally returns True."""
        assert is_feature_enabled(db, tenant_id=1, feature_key="video_analysis") is True

    def test_is_feature_enabled_global_false(self, db, seed_feature_flags):
        """Disabled global flag returns False."""
        flag = db.query(FeatureFlag).filter(FeatureFlag.key == "video_analysis").first()
        flag.enabled_globally = False
        db.commit()
        assert is_feature_enabled(db, tenant_id=1, feature_key="video_analysis") is False

    def test_tenant_override_true(self, db, seed_feature_flags):
        """Override enables feature even if globally disabled."""
        flag = db.query(FeatureFlag).filter(FeatureFlag.key == "video_analysis").first()
        flag.enabled_globally = False
        db.commit()

        tenant = Tenant(name="OverrideTest", slug="override-test")
        db.add(tenant)
        db.commit()

        override = TenantFeatureOverride(tenant_id=tenant.id, feature_flag_id=flag.id, enabled=True)
        db.add(override)
        db.commit()

        assert is_feature_enabled(db, tenant_id=tenant.id, feature_key="video_analysis") is True

    def test_tenant_override_false(self, db, seed_feature_flags):
        """Override disables feature even if globally enabled."""
        flag = db.query(FeatureFlag).filter(FeatureFlag.key == "video_analysis").first()
        # Globally enabled by default

        tenant = Tenant(name="OverrideTest2", slug="override-test-2")
        db.add(tenant)
        db.commit()

        override = TenantFeatureOverride(tenant_id=tenant.id, feature_flag_id=flag.id, enabled=False)
        db.add(override)
        db.commit()

        assert is_feature_enabled(db, tenant_id=tenant.id, feature_key="video_analysis") is False

    def test_cache_invalidation(self, db, seed_feature_flags):
        """Changing flag invalidates cache."""
        tenant_id = 1
        # First call caches the result
        result1 = is_feature_enabled(db, tenant_id=tenant_id, feature_key="video_analysis")
        assert result1 is True

        # Change in DB without invalidating cache
        flag = db.query(FeatureFlag).filter(FeatureFlag.key == "video_analysis").first()
        flag.enabled_globally = False
        db.commit()

        # Should still get cached True
        result2 = is_feature_enabled(db, tenant_id=tenant_id, feature_key="video_analysis")
        assert result2 is True

        # Invalidate cache
        invalidate_cache()

        # Now should get False
        result3 = is_feature_enabled(db, tenant_id=tenant_id, feature_key="video_analysis")
        assert result3 is False


class TestAdminEndpoints:
    def test_list_feature_flags_endpoint(self, platform_admin_client, seed_feature_flags):
        """Admin can list all flags."""
        resp = platform_admin_client.get("/api/admin/feature-flags")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 7
        keys = {f["key"] for f in data}
        assert "video_analysis" in keys
        assert "batch_analysis" in keys

    def test_toggle_feature_flag_endpoint(self, platform_admin_client, seed_feature_flags, db):
        """Admin can toggle flag."""
        flag = db.query(FeatureFlag).filter(FeatureFlag.key == "video_analysis").first()
        assert flag.enabled_globally is True

        resp = platform_admin_client.put(f"/api/admin/feature-flags/{flag.id}", json={"enabled_globally": False})
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled_globally"] is False
        assert data["key"] == "video_analysis"

        db.refresh(flag)
        assert flag.enabled_globally is False

    def test_set_tenant_override_endpoint(self, platform_admin_client, seed_feature_flags, db):
        """Admin can set override for a tenant."""
        # Find the platform admin's tenant
        user = db.query(User).filter(User.email == "platformadmin@test.com").first()
        tenant_id = user.tenant_id

        flag = db.query(FeatureFlag).filter(FeatureFlag.key == "video_analysis").first()
        # Globally enabled, override to disable
        resp = platform_admin_client.put(
            f"/api/admin/tenants/{tenant_id}/features/{flag.id}",
            json={"enabled": False}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["flag"] == "video_analysis"

        override = db.query(TenantFeatureOverride).filter(
            TenantFeatureOverride.tenant_id == tenant_id,
            TenantFeatureOverride.feature_flag_id == flag.id
        ).first()
        assert override is not None
        assert override.enabled is False

    def test_delete_tenant_override_endpoint(self, platform_admin_client, seed_feature_flags, db):
        """Admin can delete override."""
        user = db.query(User).filter(User.email == "platformadmin@test.com").first()
        tenant_id = user.tenant_id

        flag = db.query(FeatureFlag).filter(FeatureFlag.key == "video_analysis").first()

        # First create an override
        override = TenantFeatureOverride(tenant_id=tenant_id, feature_flag_id=flag.id, enabled=False)
        db.add(override)
        db.commit()

        resp = platform_admin_client.delete(f"/api/admin/tenants/{tenant_id}/features/{flag.id}")
        assert resp.status_code == 200

        override = db.query(TenantFeatureOverride).filter(
            TenantFeatureOverride.tenant_id == tenant_id,
            TenantFeatureOverride.feature_flag_id == flag.id
        ).first()
        assert override is None


class TestPermissionChecks:
    def test_regular_user_cannot_access_flag_endpoints(self, auth_client, seed_feature_flags):
        """Regular user gets 403 on feature flag admin endpoints."""
        endpoints = [
            ("get", "/api/admin/feature-flags"),
            ("put", "/api/admin/feature-flags/1"),
            ("get", "/api/admin/tenants/1/features"),
            ("put", "/api/admin/tenants/1/features/1"),
            ("delete", "/api/admin/tenants/1/features/1"),
        ]
        for method, url in endpoints:
            if method == "get":
                resp = auth_client.get(url)
            elif method == "put":
                resp = auth_client.put(url, json={"enabled_globally": True})
            elif method == "delete":
                resp = auth_client.delete(url)
            assert resp.status_code == 403, f"Expected 403 for {method.upper()} {url}, got {resp.status_code}"


class TestRequireFeatureDependency:
    def test_require_feature_dependency(self, db, seed_feature_flags):
        """Test the require_feature() middleware works."""
        from app.backend.middleware.auth import require_feature

        tenant = Tenant(name="DepTest", slug="dep-test")
        db.add(tenant)
        db.commit()

        user = User(email="dep@test.com", hashed_password="x", tenant_id=tenant.id)
        db.add(user)
        db.commit()

        # Feature enabled globally
        dep = require_feature("video_analysis")
        result = dep(current_user=user, db=db)
        assert result == user

        # Disable globally
        flag = db.query(FeatureFlag).filter(FeatureFlag.key == "video_analysis").first()
        flag.enabled_globally = False
        db.commit()
        invalidate_cache()

        dep = require_feature("video_analysis")
        with pytest.raises(HTTPException) as exc_info:
            dep(current_user=user, db=db)
        assert exc_info.value.status_code == 403
        assert "not available" in exc_info.value.detail
