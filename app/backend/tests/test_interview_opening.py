"""Tests for tenant custom interview opening."""
import pytest

from app.backend.services.interview_opening_service import (
    apply_tenant_opening_to_kit,
    render_interview_opening,
    validate_opening_template,
    default_opening_text,
    OPENING_ADMIN_FIELDS,
)
from app.backend.models.db_models import VoiceTenantConfig, Tenant


class TestRenderInterviewOpening:
    def test_replaces_allowed_placeholders(self):
        script = render_interview_opening(
            "Hi {candidate_first_name}, this is {bot_name} from {company_name} about {role_title}.",
            candidate_first_name="Alex",
            bot_name="ARIA",
            company_name="Acme",
            role_title="Engineer",
        )
        assert script == "Hi Alex, this is ARIA from Acme about Engineer."

    def test_leaves_unknown_placeholders(self):
        script = render_interview_opening("Hello {unknown}", candidate_first_name="Alex")
        assert script == "Hello {unknown}"

    def test_validate_rejects_unknown_placeholder(self):
        issues = validate_opening_template("Hi {bad_placeholder}")
        assert issues
        assert "Unknown placeholder" in issues[0]

    def test_validate_rejects_empty_when_required(self):
        assert validate_opening_template("")
        assert validate_opening_template("   ")

    def test_default_opening_uses_first_name(self):
        text = default_opening_text(
            candidate_name="Jordan Lee",
            role_title="Analyst",
            company_name="ThetaLogics",
            bot_name="ARIA",
        )
        assert "Jordan" in text
        assert "ThetaLogics" in text
        assert "Analyst" in text


class TestApplyTenantOpeningToKit:
    def test_applies_custom_opening_to_kit(self, db):
        tenant = Tenant(name="Acme Corp", slug="acme-opening-test")
        db.add(tenant)
        db.flush()
        config = VoiceTenantConfig(
            tenant_id=tenant.id,
            use_custom_interview_opening=True,
            interview_opening_script=(
                "Hi {candidate_first_name}, {bot_name} from {company_name} about {role_title}."
            ),
        )
        db.add(config)
        db.commit()

        kit = {"open": {"script": "", "recruiter_owned": True}, "threads": []}
        updated = apply_tenant_opening_to_kit(
            kit,
            db,
            tenant.id,
            candidate_name="Sam Taylor",
            role_title="Designer",
        )
        assert "Sam" in updated["open"]["script"]
        assert updated["open"]["recruiter_owned"] is False

    def test_skips_when_disabled(self, db):
        tenant = Tenant(name="Beta Corp", slug="beta-opening-test")
        db.add(tenant)
        db.flush()
        config = VoiceTenantConfig(
            tenant_id=tenant.id,
            use_custom_interview_opening=False,
            interview_opening_script="Hi {candidate_first_name}",
        )
        db.add(config)
        db.commit()

        kit = {"open": {"script": "", "recruiter_owned": True}}
        updated = apply_tenant_opening_to_kit(kit, db, tenant.id, candidate_name="Sam")
        assert updated["open"]["script"] == ""


class TestOpeningAdminFields:
    def test_admin_field_names(self):
        assert "interview_opening_script" in OPENING_ADMIN_FIELDS
        assert "use_custom_interview_opening" in OPENING_ADMIN_FIELDS


class TestOpeningAdminRbac:
    def test_recruiter_cannot_update_opening(self, client, sample_user):
        login = client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "TestPass123!"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        resp = client.put(
            "/api/voice/settings",
            json={
                "use_custom_interview_opening": True,
                "interview_opening_script": "Hi {candidate_first_name}",
            },
            headers=headers,
        )
        assert resp.status_code == 403
