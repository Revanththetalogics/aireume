"""Tenant RBAC — viewer read-only, recruiter/admin write access."""
import pytest


def _role_error_code(response) -> str | None:
    detail = response.json().get("detail")
    if isinstance(detail, dict):
        return detail.get("error_code")
    return None


class TestTenantRbac:
    def test_viewer_can_list_templates(self, viewer_client):
        resp = viewer_client.get("/api/templates")
        assert resp.status_code == 200

    def test_viewer_cannot_create_template(self, viewer_client):
        resp = viewer_client.post("/api/templates", json={
            "name": "Blocked Role",
            "jd_text": "We need a senior engineer with Python experience.",
        })
        assert resp.status_code == 403
        assert _role_error_code(resp) == "ROLE_FORBIDDEN"

    def test_recruiter_can_create_template(self, auth_client):
        resp = auth_client.post("/api/templates", json={
            "name": "Allowed Role",
            "jd_text": "We need a senior engineer with Python experience.",
        })
        assert resp.status_code == 200

    def test_viewer_cannot_update_result_status(self, viewer_client, db):
        from app.backend.models.db_models import User, Candidate, ScreeningResult

        user = db.query(User).filter(User.email == "viewer@viewercorp.com").first()
        candidate = Candidate(
            tenant_id=user.tenant_id,
            name="RBAC Candidate",
            email="rbac@example.com",
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        result = ScreeningResult(
            tenant_id=user.tenant_id,
            candidate_id=candidate.id,
            resume_text="Resume text",
            jd_text="Job description text",
            status="pending",
            analysis_result="{}",
            parsed_data="{}",
        )
        db.add(result)
        db.commit()
        db.refresh(result)

        resp = viewer_client.put(
            f"/api/results/{result.id}/status",
            json={"status": "shortlisted"},
        )
        assert resp.status_code == 403
        assert _role_error_code(resp) == "ROLE_FORBIDDEN"

    def test_admin_can_delete_template(self, auth_client):
        create = auth_client.post("/api/templates", json={
            "name": "Delete Me",
            "jd_text": "Temporary JD for delete RBAC test.",
        })
        assert create.status_code == 200
        template_id = create.json()["id"]

        delete = auth_client.delete(f"/api/templates/{template_id}")
        assert delete.status_code == 200

    def test_viewer_cannot_delete_template(self, viewer_client, db):
        from app.backend.models.db_models import User, RoleTemplate

        viewer = db.query(User).filter(User.email == "viewer@viewercorp.com").first()
        template = RoleTemplate(
            tenant_id=viewer.tenant_id,
            name="Viewer Delete Test",
            jd_text="JD text for delete test.",
        )
        db.add(template)
        db.commit()
        db.refresh(template)

        resp = viewer_client.delete(f"/api/templates/{template.id}")
        assert resp.status_code == 403
