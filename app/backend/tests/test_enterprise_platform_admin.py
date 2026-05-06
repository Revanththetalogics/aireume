"""
Enterprise Platform Admin tests:
- Security event recording
- Impersonation lifecycle
- GDPR erasure
- Plan-feature entitlement mapping
"""
import pytest
from app.backend.models.db_models import (
    User, Tenant, SecurityEvent, ImpersonationSession, ErasureLog,
    SubscriptionPlan, FeatureFlag, PlanFeature
)


# ─── Security Events ──────────────────────────────────────────────────────────

class TestSecurityEvents:
    def test_login_failure_records_security_event(self, client, db):
        """Failed logins should create security_events rows."""
        # Ensure a user exists
        from app.backend.routes.auth import pwd_context
        tenant = Tenant(name="SecTest", slug="sectest")
        db.add(tenant)
        db.commit()
        user = User(email="sec@example.com", hashed_password=pwd_context.hash("right"), tenant_id=tenant.id)
        db.add(user)
        db.commit()

        resp = client.post("/api/auth/login", json={"email": "sec@example.com", "password": "wrong"})
        assert resp.status_code == 401

        events = db.query(SecurityEvent).filter(
            SecurityEvent.event_type == "login_failure"
        ).all()
        assert len(events) >= 1
        assert any("sec@example.com" in (e.details or "") for e in events)

    def test_login_success_records_security_event(self, client, db):
        from app.backend.routes.auth import pwd_context
        tenant = Tenant(name="SecTest2", slug="sectest2")
        db.add(tenant)
        db.commit()
        user = User(email="sec2@example.com", hashed_password=pwd_context.hash("pass"), tenant_id=tenant.id)
        db.add(user)
        db.commit()

        resp = client.post("/api/auth/login", json={"email": "sec2@example.com", "password": "pass"})
        assert resp.status_code == 200

        events = db.query(SecurityEvent).filter(
            SecurityEvent.event_type == "login_success",
            SecurityEvent.user_id == user.id
        ).all()
        assert len(events) >= 1

    def test_security_events_admin_endpoint(self, platform_admin_client, db):
        # Seed an event directly
        event = SecurityEvent(event_type="suspicious_activity", ip_address="1.2.3.4")
        db.add(event)
        db.commit()

        resp = platform_admin_client.get("/api/admin/security-events")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert any(i["event_type"] == "suspicious_activity" for i in data["items"])


# ─── Impersonation ────────────────────────────────────────────────────────────

class TestImpersonation:
    def test_impersonate_creates_session(self, platform_admin_client, db):
        from app.backend.routes.auth import pwd_context
        tenant = Tenant(name="ImpTest", slug="imptest")
        db.add(tenant)
        db.commit()
        target = User(email="target@example.com", hashed_password=pwd_context.hash("x"), tenant_id=tenant.id)
        db.add(target)
        db.commit()

        resp = platform_admin_client.post(f"/api/admin/impersonate/{target.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "impersonation_token" in data
        assert data["target_user"]["email"] == "target@example.com"

        sessions = db.query(ImpersonationSession).filter(ImpersonationSession.target_user_id == target.id).all()
        assert len(sessions) == 1

    def test_list_impersonation_sessions(self, platform_admin_client, db):
        from app.backend.routes.auth import pwd_context
        tenant = Tenant(name="ImpTest2", slug="imptest2")
        db.add(tenant)
        db.commit()
        target = User(email="target2@example.com", hashed_password=pwd_context.hash("x"), tenant_id=tenant.id)
        db.add(target)
        db.commit()

        platform_admin_client.post(f"/api/admin/impersonate/{target.id}")

        resp = platform_admin_client.get("/api/admin/impersonate/sessions")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_revoke_impersonation_session(self, platform_admin_client, db):
        from app.backend.routes.auth import pwd_context
        tenant = Tenant(name="ImpTest3", slug="imptest3")
        db.add(tenant)
        db.commit()
        target = User(email="target3@example.com", hashed_password=pwd_context.hash("x"), tenant_id=tenant.id)
        db.add(target)
        db.commit()

        create_resp = platform_admin_client.post(f"/api/admin/impersonate/{target.id}")
        session_id = db.query(ImpersonationSession).first().id

        del_resp = platform_admin_client.delete(f"/api/admin/impersonate/sessions/{session_id}")
        assert del_resp.status_code == 200

        session = db.query(ImpersonationSession).filter(ImpersonationSession.id == session_id).first()
        assert session.revoked_at is not None


# ─── GDPR Erasure ─────────────────────────────────────────────────────────────

class TestGDPRDataErasure:
    def test_erasure_requires_confirmation(self, platform_admin_client, db):
        from app.backend.routes.auth import pwd_context
        tenant = Tenant(name="EraseTest", slug="erasetest")
        db.add(tenant)
        db.commit()

        resp = platform_admin_client.post(f"/api/admin/tenants/{tenant.id}/anonymize", json={"confirm": False})
        assert resp.status_code == 400

    def test_erasure_anonymizes_and_suspends(self, platform_admin_client, db):
        from app.backend.routes.auth import pwd_context
        tenant = Tenant(name="EraseTest2", slug="erasetest2")
        db.add(tenant)
        db.commit()
        user = User(email="erase@example.com", hashed_password=pwd_context.hash("x"), tenant_id=tenant.id)
        db.add(user)
        db.commit()

        resp = platform_admin_client.post(f"/api/admin/tenants/{tenant.id}/anonymize", json={"confirm": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"

        db.refresh(tenant)
        assert tenant.suspended_at is not None

        logs = db.query(ErasureLog).filter(ErasureLog.tenant_id == tenant.id).all()
        assert len(logs) >= 1
        assert logs[0].status == "completed"

    def test_erasure_logs_endpoint(self, platform_admin_client, db):
        from app.backend.routes.auth import pwd_context
        tenant = Tenant(name="EraseTest3", slug="erasetest3")
        db.add(tenant)
        db.commit()

        platform_admin_client.post(f"/api/admin/tenants/{tenant.id}/anonymize", json={"confirm": True})

        resp = platform_admin_client.get(f"/api/admin/tenants/{tenant.id}/anonymize")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ─── Plan-Feature Entitlement ─────────────────────────────────────────────────

class TestPlanFeatureEntitlement:
    def test_plan_feature_mapping_crud(self, platform_admin_client_with_plans, db):
        # Seed a feature flag
        flag = FeatureFlag(key="test_feature", display_name="Test Feature", enabled_globally=True)
        db.add(flag)
        db.commit()

        plan = db.query(SubscriptionPlan).first()
        assert plan is not None

        # PUT mapping
        resp = platform_admin_client_with_plans.put(
            f"/api/admin/plans/{plan.id}/features/{flag.id}",
            json={"enabled": False}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["feature_key"] == "test_feature"

        # GET mappings
        resp = platform_admin_client_with_plans.get(f"/api/admin/plans/{plan.id}/features")
        assert resp.status_code == 200
        assert any(m["feature_flag_id"] == flag.id for m in resp.json())

        # DELETE mapping
        resp = platform_admin_client_with_plans.delete(f"/api/admin/plans/{plan.id}/features/{flag.id}")
        assert resp.status_code == 200

        mapping = db.query(PlanFeature).filter(
            PlanFeature.plan_id == plan.id, PlanFeature.feature_flag_id == flag.id
        ).first()
        assert mapping is None
