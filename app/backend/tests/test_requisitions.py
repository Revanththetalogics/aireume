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
    intake_has_minimum_content,
    intake_screening_ready,
    migrate_legacy_data,
    get_or_create_tenant_settings,
    resolve_role_picker_id,
    requisition_has_hiring_manager,
    suggest_intake_from_jd,
    sync_working_criteria_v0,
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
        assert intake_gate_blocks(settings, req, db) is True
        assert intake_has_minimum_content(req) is False

    def test_intake_gate_ready_after_intake_and_hm(self, db, auth_client):
        user = _admin_user(db)
        hm = User(
            email="hm-gate@testcorp.com",
            hashed_password=_hash_password("pass"),
            tenant_id=user.tenant_id,
            role="hiring_manager",
            is_active=True,
            email_verified=True,
        )
        db.add(hm)
        db.flush()
        settings = get_or_create_tenant_settings(db, user.tenant_id)
        settings.intake_gate_mode = "warn"
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="Ready Req",
            jd_text="Kubernetes and Go required for platform engineering.",
            primary_hiring_manager_id=hm.id,
        )
        req.intake_json = json.dumps({
            "screen_focus_topics": ["Ownership of on-call rotation"],
        })
        sync_working_criteria_v0(db, req)
        db.commit()
        assert intake_has_minimum_content(req) is True
        assert requisition_has_hiring_manager(req, db) is True
        assert intake_screening_ready(req, db) is True
        assert intake_gate_blocks(settings, req, db) is False

    def test_intake_gate_warn_blocks_without_intake(self, db, auth_client):
        user = _admin_user(db)
        hm = User(
            email="hm-no-intake@testcorp.com",
            hashed_password=_hash_password("pass"),
            tenant_id=user.tenant_id,
            role="hiring_manager",
            is_active=True,
            email_verified=True,
        )
        db.add(hm)
        db.flush()
        settings = get_or_create_tenant_settings(db, user.tenant_id)
        settings.intake_gate_mode = "warn"
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="No Intake",
            jd_text="Python and SQL required for analytics engineering role.",
            primary_hiring_manager_id=hm.id,
        )
        db.commit()
        assert intake_screening_ready(req, db) is False
        assert intake_gate_blocks(settings, req, db) is True

    def test_intake_gate_block_requires_hm_approval(self, db, auth_client):
        user = _admin_user(db)
        hm = User(
            email="hm-block@testcorp.com",
            hashed_password=_hash_password("pass"),
            tenant_id=user.tenant_id,
            role="hiring_manager",
            is_active=True,
            email_verified=True,
        )
        db.add(hm)
        db.flush()
        settings = get_or_create_tenant_settings(db, user.tenant_id)
        settings.intake_gate_mode = "block"
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="Block Until Approve",
            jd_text="Java and Spring required for backend engineering.",
            primary_hiring_manager_id=hm.id,
        )
        req.intake_json = json.dumps({"must_haves": ["Java"]})
        req.intake_status = "pending_hm"
        db.commit()
        assert intake_screening_ready(req, db) is True
        assert intake_gate_blocks(settings, req, db) is True

    def test_hm_approval_always_locks_criteria(self, db, auth_client):
        user = _admin_user(db)
        hm = User(
            email="hm-approve@testcorp.com",
            hashed_password=_hash_password("pass"),
            tenant_id=user.tenant_id,
            role="hiring_manager",
            is_active=True,
            email_verified=True,
        )
        db.add(hm)
        db.flush()
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="Approve Locks V1",
            jd_text="Python required for data engineering.",
            primary_hiring_manager_id=hm.id,
        )
        req.intake_json = json.dumps({"must_haves": ["Python"], "screen_focus_topics": ["ETL ownership"]})
        sync_working_criteria_v0(db, req)
        db.commit()
        assert (req.current_criteria_version or 0) == 0
        calibrate_requisition(db, req, user_id=hm.id)
        db.commit()
        assert req.intake_status != "approved"
        assert req.current_criteria_version == 1

        req.intake_status = "approved"
        calibrate_requisition(db, req, user_id=hm.id)
        db.commit()
        assert req.current_criteria_version == 2

    def test_suggest_intake_from_jd(self, db, auth_client):
        user = _admin_user(db)
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="Data Engineer",
            jd_text="Required: Python, SQL, Spark. Nice: Airflow. Build ETL pipelines.",
        )
        db.commit()
        suggested = suggest_intake_from_jd(req)
        assert suggested.get("must_haves")
        assert suggested.get("screen_focus_topics")

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

    def test_update_criteria_endpoint(self, auth_client, db):
        user = _admin_user(db)
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="Criteria Edit",
            jd_text="Python and SQL required for analytics engineering role.",
        )
        calibrate_requisition(db, req, user_id=user.id)
        db.commit()
        resp = auth_client.put(
            f"/api/requisitions/{req.id}/criteria",
            json={"must_haves": ["Python", "SQL", "Stakeholder updates"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_criteria_version"] >= 2
        assert "Stakeholder updates" in data["calibrated_criteria_json"]["must_haves"]

        versions = auth_client.get(f"/api/requisitions/{req.id}/criteria-versions")
        assert versions.status_code == 200
        assert len(versions.json()) >= 2

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
        hm = User(
            tenant_id=user.tenant_id,
            email="hm-analyze-link@testcorp.com",
            hashed_password=_hash_password("pass"),
            role="hiring_manager",
            is_active=True,
            email_verified=True,
        )
        db.add(hm)
        db.flush()
        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="Analyze Link Test",
            jd_text=_JD,
            primary_hiring_manager_id=hm.id,
        )
        req.intake_json = json.dumps({
            "screen_focus_topics": ["Backend API ownership"],
            "must_haves": ["python", "fastapi"],
        })
        sync_working_criteria_v0(db, req)
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


class TestHmRequestGovernance:
    def _recruiter_client(self, client, db):
        admin = _admin_user(db)
        user = User(
            tenant_id=admin.tenant_id,
            email="recruiter-hm-req@testcorp.com",
            hashed_password=_hash_password("pass"),
            role="recruiter",
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        db.commit()
        login = client.post("/api/auth/login", json={"email": user.email, "password": "pass"})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        return user

    def test_recruiter_submits_hm_request(self, client, db, auth_client):
        from app.backend.tests.test_workflows_e2e import _JD

        self._recruiter_client(client, db)
        admin = _admin_user(db)
        req = create_requisition(
            db,
            tenant_id=admin.tenant_id,
            created_by=admin.id,
            title="HM Request Test",
            jd_text=_JD,
        )
        db.commit()

        resp = client.post(
            f"/api/requisitions/{req.id}/hm-request",
            json={"email": "new.hm@testcorp.com", "notes": "Finance director"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["hm_request_email"] == "new.hm@testcorp.com"
        assert data["hm_request_status"] == "pending"

    def test_admin_approves_hm_request(self, db, auth_client):
        from app.backend.tests.test_workflows_e2e import _JD
        from app.backend.services.requisition_service import request_hm_for_requisition

        admin = _admin_user(db)
        recruiter = User(
            tenant_id=admin.tenant_id,
            email="recruiter-approve-hm@testcorp.com",
            hashed_password=_hash_password("pass"),
            role="recruiter",
            is_active=True,
            email_verified=True,
        )
        db.add(recruiter)
        db.commit()
        req = create_requisition(
            db,
            tenant_id=admin.tenant_id,
            created_by=recruiter.id,
            title="HM Approve Test",
            jd_text=_JD,
        )
        request_hm_for_requisition(
            db, req, email="approve.hm@testcorp.com", requested_by=recruiter.id,
        )
        db.commit()

        resp = auth_client.post(f"/api/requisitions/{req.id}/hm-request/approve")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["primary_hiring_manager_email"] == "approve.hm@testcorp.com"
        assert data["hm_request_status"] == "approved"

        hm = db.query(User).filter(User.email == "approve.hm@testcorp.com").first()
        assert hm is not None
        assert hm.role == "hiring_manager"

    def test_admin_cannot_use_request_endpoint(self, auth_client, db):
        from app.backend.tests.test_workflows_e2e import _JD

        admin = _admin_user(db)
        req = create_requisition(
            db,
            tenant_id=admin.tenant_id,
            created_by=admin.id,
            title="Admin Request Blocked",
            jd_text=_JD,
        )
        db.commit()

        resp = auth_client.post(
            f"/api/requisitions/{req.id}/hm-request",
            json={"email": "blocked@testcorp.com"},
        )
        assert resp.status_code == 400


class TestPipelineBackfill:
    def test_backfill_from_legacy_screening(self, db, auth_client):
        from app.backend.tests.test_workflows_e2e import _JD
        from app.backend.services.requisition_service import (
            backfill_pipeline_from_screenings,
            create_requisition,
        )
        from app.backend.models.db_models import Candidate, RequisitionCandidate, ScreeningResult, RoleTemplate

        user = _admin_user(db)
        tpl = RoleTemplate(
            tenant_id=user.tenant_id,
            name="Legacy FP&A",
            jd_text=_JD,
        )
        db.add(tpl)
        db.flush()

        cand = Candidate(tenant_id=user.tenant_id, name="Legacy Cand", email="legacy@test.com")
        db.add(cand)
        db.flush()

        sr = ScreeningResult(
            tenant_id=user.tenant_id,
            candidate_id=cand.id,
            role_template_id=tpl.id,
            resume_text="x",
            jd_text=_JD,
            parsed_data="{}",
            analysis_result='{"recommendation":"consider","fit_score":65}',
            deterministic_score=65,
            status="pending",
        )
        db.add(sr)
        db.flush()

        req = create_requisition(
            db,
            tenant_id=user.tenant_id,
            created_by=user.id,
            title="Financial Analyst",
            jd_text=_JD,
        )
        req.legacy_role_template_id = tpl.id
        db.flush()

        result = backfill_pipeline_from_screenings(db, req, commit=True)
        assert result["added"] >= 1

        rc = db.query(RequisitionCandidate).filter(
            RequisitionCandidate.requisition_id == req.id,
            RequisitionCandidate.candidate_id == cand.id,
        ).first()
        assert rc is not None
        assert rc.screening_result_id == sr.id
