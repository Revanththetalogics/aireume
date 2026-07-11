"""Tests for requisition system — CRUD, calibration, HM scoping, intake gate."""
import json

import pytest

from app.backend.models.db_models import (
    Requisition,
    RoleTemplate,
    User,
)
from app.backend.routes.auth import _hash_password
from app.backend.services.requisition_service import (
    build_default_intake,
    calibrate_requisition,
    create_requisition,
    ensure_legacy_role_template,
    intake_gate_blocks,
    migrate_legacy_data,
    get_or_create_tenant_settings,
    resolve_role_picker_id,
)


def _admin_user(db):
    return db.query(User).filter(User.email == "admin@testcorp.com").first()


class TestRequisitionService:
    def test_create_requisition(self, db, auth_client):
        user = _admin_user(db)
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="Senior Engineer",
            jd_text="We need Python and AWS experience for backend services.",
        )
        db.commit()
        assert req.id is not None
        assert req.status == "draft"
        assert req.legacy_role_template_id is not None
        intake = json.loads(req.intake_json)
        assert intake["role_title"] == "Senior Engineer"

    def test_calibrate_merges_jd_and_intake(self, db, auth_client):
        user = _admin_user(db)
        intake = build_default_intake("Data Analyst", "SQL and Tableau required.")
        intake["must_haves"] = ["Stakeholder communication"]
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="Data Analyst",
            jd_text="SQL and Tableau required. Python is a plus.",
        )
        req.intake_json = json.dumps(intake)
        db.commit()
        version = calibrate_requisition(db, req, user_id=user.id)
        db.commit()
        criteria = json.loads(version.criteria_json)
        assert "Stakeholder communication" in criteria["must_haves"]
        assert req.status == "calibrated"
        assert req.current_criteria_version == 1

    def test_intake_gate_block(self, db, auth_client):
        user = _admin_user(db)
        settings = get_or_create_tenant_settings(db, user.tenant_id)
        settings.intake_gate_mode = "block"
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="Uncalibrated",
            jd_text="Some JD text here for testing purposes only.",
        )
        db.commit()
        assert intake_gate_blocks(settings, req) is True

    def test_migrate_role_templates(self, db, auth_client):
        user = _admin_user(db)
        tpl = RoleTemplate(
            tenant_id=user.tenant_id,
            name="Legacy Role",
            jd_text="Legacy JD content for migration test.",
            created_by=user.id,
        )
        db.add(tpl)
        db.commit()
        count = migrate_legacy_data(db, user.tenant_id)
        db.commit()
        assert count >= 1
        req = db.query(Requisition).filter(Requisition.tenant_id == user.tenant_id).first()
        assert req.legacy_role_template_id == tpl.id
        assert req.title == "Legacy Role"

    def test_resolve_role_picker_id(self, db, auth_client):
        user = _admin_user(db)
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="Picker Test",
            jd_text="Resolve picker id from requisition for interviews.",
        )
        db.commit()
        jd, name, tpl_id, req_id = resolve_role_picker_id(db, user.tenant_id, req.id)
        assert req_id == req.id
        assert tpl_id == req.legacy_role_template_id
        assert name == "Picker Test"
        assert "interviews" in jd


class TestRequisitionApi:
    def test_create_and_list(self, auth_client):
        resp = auth_client.post("/api/requisitions", json={
            "title": "Product Manager",
            "jd_text": "Lead product discovery and roadmap for B2B SaaS platform.",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Product Manager"

        listed = auth_client.get("/api/requisitions")
        assert listed.status_code == 200
        assert any(r["title"] == "Product Manager" for r in listed.json())

    def test_calibrate_endpoint(self, auth_client, db):
        user = _admin_user(db)
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="API Calibrate",
            jd_text="Kubernetes and Go required for platform engineering.",
        )
        db.commit()
        resp = auth_client.post(f"/api/requisitions/{req.id}/calibrate", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_calibrated"] is True
        assert data["current_criteria_version"] >= 1

    def test_hm_scoped_list(self, client, db, auth_client):
        admin = _admin_user(db)
        hm = User(
            tenant_id=admin.tenant_id,
            email="hm@testcorp.com",
            hashed_password=_hash_password("HmPass123!"),
            role="hiring_manager",
            is_active=True,
            email_verified=True,
        )
        db.add(hm)
        db.commit()
        db.refresh(hm)

        req = create_requisition(
            db,
            tenant_id=admin.tenant_id,
            created_by=admin.id,
            title="HM Role",
            jd_text="JD for HM scoped listing test.",
            primary_hiring_manager_id=hm.id,
        )
        create_requisition(
            db,
            tenant_id=admin.tenant_id,
            created_by=admin.id,
            title="Other Role",
            jd_text="Another JD not assigned to HM.",
        )
        db.commit()

        login = client.post("/api/auth/login", json={
            "email": "hm@testcorp.com",
            "password": "HmPass123!",
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        resp = client.get(
            "/api/requisitions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        titles = [r["title"] for r in resp.json()]
        assert "HM Role" in titles
        assert "Other Role" not in titles

    def test_analyze_with_requisition_id_links_pipeline(self, auth_client, db):
        """E2E API: analyze resume scoped to requisition → pipeline row created."""
        import io
        from unittest.mock import AsyncMock, patch

        from app.backend.models.db_models import RequisitionCandidate, ScreeningResult
        from app.backend.tests.test_workflows_e2e import _JD, _PIPELINE_RESULT, _RESUME

        user = _admin_user(db)
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="Analyze Link Test",
            jd_text=_JD,
        )
        db.commit()

        with patch("app.backend.routes.analyze.parse_resume", return_value={
            "raw_text": "Jane Dev python fastapi postgresql docker",
            "skills": ["python", "fastapi", "postgresql", "docker"],
            "education": [], "work_experience": [],
            "contact_info": {"name": "Jane Dev", "email": "jane@dev.com"},
        }), patch("app.backend.routes.analyze.analyze_gaps", return_value={}), \
           patch("app.backend.routes.analyze.run_hybrid_pipeline",
                 new_callable=AsyncMock, return_value=_PIPELINE_RESULT):
            resp = auth_client.post(
                "/api/analyze",
                data={"job_description": _JD, "requisition_id": str(req.id)},
                files={"resume": ("resume.txt", io.BytesIO(_RESUME), "text/plain")},
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body.get("requisition_id") == req.id
        result_id = body.get("result_id")
        assert result_id

        row = db.query(ScreeningResult).filter(ScreeningResult.id == result_id).first()
        assert row is not None
        assert row.requisition_id == req.id

        rc = db.query(RequisitionCandidate).filter(
            RequisitionCandidate.requisition_id == req.id,
            RequisitionCandidate.candidate_id == row.candidate_id,
        ).first()
        assert rc is not None
