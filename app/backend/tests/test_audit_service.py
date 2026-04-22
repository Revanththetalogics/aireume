"""Unit tests for the audit logging service."""
import json
import pytest
from app.backend.models.db_models import AuditLog, Tenant, User
from app.backend.services.audit_service import log_audit


def _create_test_user(db):
    """Helper to create a tenant and user for audit tests."""
    tenant = Tenant(name="Audit Test Corp", slug="audit-test-corp")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    user = User(
        tenant_id=tenant.id,
        email="audit.user@test.com",
        hashed_password="hashed_password_here",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestLogAudit:
    def test_log_audit_creates_entry_with_correct_fields(self, db):
        user = _create_test_user(db)

        entry = log_audit(
            db,
            actor=user,
            action="tenant.suspend",
            resource_type="tenant",
            resource_id=42,
            details={"reason": "non-payment"},
            ip_address="192.168.1.1",
        )

        assert entry.id is not None
        assert entry.actor_user_id == user.id
        assert entry.actor_email == user.email
        assert entry.action == "tenant.suspend"
        assert entry.resource_type == "tenant"
        assert entry.resource_id == 42
        assert json.loads(entry.details) == {"reason": "non-payment"}
        assert entry.ip_address == "192.168.1.1"
        assert entry.created_at is not None

    def test_log_audit_with_all_optional_fields(self, db):
        user = _create_test_user(db)

        entry = log_audit(
            db,
            actor=user,
            action="plan.change",
            resource_type="subscription_plan",
            resource_id=7,
            details={"old_plan": "free", "new_plan": "pro"},
            ip_address="10.0.0.5",
        )

        assert entry.actor_user_id == user.id
        assert entry.action == "plan.change"
        assert entry.resource_type == "subscription_plan"
        assert entry.resource_id == 7
        assert json.loads(entry.details) == {"old_plan": "free", "new_plan": "pro"}
        assert entry.ip_address == "10.0.0.5"

    def test_log_audit_with_minimal_fields(self, db):
        user = _create_test_user(db)

        entry = log_audit(
            db,
            actor=user,
            action="user.login",
            resource_type="user",
        )

        assert entry.actor_user_id == user.id
        assert entry.action == "user.login"
        assert entry.resource_type == "user"
        assert entry.resource_id is None
        assert json.loads(entry.details) == {}
        assert entry.ip_address is None

    def test_details_are_properly_json_serialized(self, db):
        user = _create_test_user(db)
        complex_details = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "boolean": True,
            "null_value": None,
        }

        entry = log_audit(
            db,
            actor=user,
            action="config.update",
            resource_type="feature_flag",
            details=complex_details,
        )

        parsed = json.loads(entry.details)
        assert parsed["nested"] == {"key": "value"}
        assert parsed["list"] == [1, 2, 3]
        assert parsed["boolean"] is True
        assert parsed["null_value"] is None

    def test_multiple_audit_entries_can_be_created(self, db):
        user = _create_test_user(db)

        entry1 = log_audit(
            db,
            actor=user,
            action="tenant.suspend",
            resource_type="tenant",
            resource_id=1,
        )
        entry2 = log_audit(
            db,
            actor=user,
            action="tenant.resume",
            resource_type="tenant",
            resource_id=2,
        )
        entry3 = log_audit(
            db,
            actor=user,
            action="user.delete",
            resource_type="user",
            resource_id=99,
        )

        assert entry1.id != entry2.id != entry3.id

        all_entries = db.query(AuditLog).all()
        assert len(all_entries) == 3

    def test_audit_log_entries_are_queryable_by_action_and_resource_type(self, db):
        user = _create_test_user(db)

        log_audit(db, actor=user, action="tenant.suspend", resource_type="tenant", resource_id=1)
        log_audit(db, actor=user, action="tenant.resume", resource_type="tenant", resource_id=1)
        log_audit(db, actor=user, action="user.delete", resource_type="user", resource_id=5)
        log_audit(db, actor=user, action="plan.change", resource_type="subscription_plan", resource_id=2)

        tenant_actions = db.query(AuditLog).filter(AuditLog.action == "tenant.suspend").all()
        assert len(tenant_actions) == 1
        assert tenant_actions[0].resource_type == "tenant"

        tenant_entries = db.query(AuditLog).filter(AuditLog.resource_type == "tenant").all()
        assert len(tenant_entries) == 2

        user_entries = db.query(AuditLog).filter(AuditLog.resource_type == "user").all()
        assert len(user_entries) == 1
        assert user_entries[0].action == "user.delete"

        plan_entries = db.query(AuditLog).filter(
            AuditLog.action == "plan.change",
            AuditLog.resource_type == "subscription_plan",
        ).all()
        assert len(plan_entries) == 1
        assert plan_entries[0].resource_id == 2
