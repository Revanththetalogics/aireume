"""Phase 2 enterprise RBAC tests."""
import secrets
from datetime import datetime, timedelta, timezone

import pytest


class TestProjectsRbac:
    def test_viewer_cannot_create_project(self, viewer_client, db):
        from app.backend.models.db_models import RoleTemplate, User

        user = db.query(User).filter(User.email == "viewer@viewercorp.com").first()
        template = RoleTemplate(
            tenant_id=user.tenant_id,
            name="Project Role",
            jd_text="Need a backend engineer.",
            created_by=user.id,
        )
        db.add(template)
        db.commit()
        db.refresh(template)

        resp = viewer_client.post("/api/projects", json={
            "role_template_id": template.id,
            "name": "Q3 Push",
            "description": "Hiring push",
            "status": "active",
        })
        assert resp.status_code == 403


class TestHandoffShareLinks:
    def test_public_handoff_via_magic_link(self, auth_client, db):
        from app.backend.models.db_models import HandoffShareLink, RoleTemplate, User

        user = db.query(User).filter(User.email == "admin@testcorp.com").first()
        template = RoleTemplate(
            tenant_id=user.tenant_id,
            name="HM Role",
            jd_text="Senior PM role",
            created_by=user.id,
        )
        db.add(template)
        db.commit()
        db.refresh(template)

        token = secrets.token_urlsafe(16)
        link = HandoffShareLink(
            token=token,
            tenant_id=user.tenant_id,
            role_template_id=template.id,
            created_by=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(link)
        db.commit()

        from fastapi.testclient import TestClient
        from app.backend.main import app

        public_client = TestClient(app)
        resp = public_client.get(f"/api/public/handoff/{token}")
        assert resp.status_code == 200
        assert resp.json()["jd_name"] == "HM Role"
        assert resp.json()["public_view"] is True


class TestTemplateOwnership:
    def test_recruiter_cannot_edit_other_owners_template(self, auth_client, db):
        from app.backend.models.db_models import RoleTemplate, User
        from app.backend.routes.auth import _hash_password

        admin = db.query(User).filter(User.email == "admin@testcorp.com").first()
        owner = User(
            tenant_id=admin.tenant_id,
            email="owner2@testcorp.com",
            hashed_password=_hash_password("OwnerPass123!"),
            role="recruiter",
            email_verified=True,
        )
        other = User(
            tenant_id=admin.tenant_id,
            email="other2@testcorp.com",
            hashed_password=_hash_password("OtherPass123!"),
            role="recruiter",
            email_verified=True,
        )
        db.add_all([owner, other])
        db.commit()
        db.refresh(owner)

        template = RoleTemplate(
            tenant_id=admin.tenant_id,
            name="Owned Role",
            jd_text="Owned JD",
            created_by=owner.id,
        )
        db.add(template)
        db.commit()
        db.refresh(template)

        login = auth_client.post("/api/auth/login", json={
            "email": "other2@testcorp.com",
            "password": "OtherPass123!",
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        auth_client.headers.update({"Authorization": f"Bearer {token}"})

        resp = auth_client.put(f"/api/templates/{template.id}", json={"name": "Hijacked"})
        assert resp.status_code == 403
