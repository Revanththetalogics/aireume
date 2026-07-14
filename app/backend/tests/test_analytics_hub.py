"""Tests for analytics hub aggregates."""
import json
from datetime import datetime, timedelta, timezone

from app.backend.models.db_models import (
    Candidate,
    Requisition,
    RequisitionCandidate,
    ScreeningResult,
    UsageLog,
    User,
)
from app.backend.services.analytics_hub_service import build_analytics_hub
from app.backend.services.screening_analytics_service import build_screening_analytics


def _admin_user(db):
    return db.query(User).filter(User.email == "admin@testcorp.com").first()


class TestAnalyticsHub:
    def test_team_slice_counts_per_recruiter(self, db, auth_client):
        user = _admin_user(db)
        other = User(
            tenant_id=user.tenant_id,
            email="recruiter2@testcorp.com",
            hashed_password=user.hashed_password,
            role="recruiter",
            is_active=True,
            email_verified=True,
        )
        db.add(other)
        db.flush()

        now = datetime.now(timezone.utc)
        db.add(UsageLog(
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="resume_analysis",
            quantity=3,
            created_at=now,
        ))
        db.add(UsageLog(
            tenant_id=user.tenant_id,
            user_id=other.id,
            action="resume_analysis",
            quantity=1,
            created_at=now,
        ))
        db.commit()

        hub = build_analytics_hub(db, user.tenant_id, period="last_30_days", slices=["team"])
        activity = {row["user_id"]: row["analyses"] for row in hub["slices"]["team"]["recruiter_activity"]}
        assert activity.get(user.id) == 3
        assert activity.get(other.id) == 1

    def test_screening_drill_down_includes_candidate_identity(self, db, auth_client):
        user = _admin_user(db)
        req = Requisition(
            tenant_id=user.tenant_id,
            title="Backend Engineer",
            jd_text="Python and PostgreSQL required for backend services.",
            created_by=user.id,
        )
        db.add(req)
        db.flush()

        cand = Candidate(
            tenant_id=user.tenant_id,
            name="Jane Doe",
            email="jane@example.com",
        )
        db.add(cand)
        db.flush()

        result = ScreeningResult(
            tenant_id=user.tenant_id,
            candidate_id=cand.id,
            requisition_id=req.id,
            resume_text="Jane Doe resume",
            jd_text=req.jd_text,
            parsed_data="{}",
            analysis_result=json.dumps({
                "fit_score": 82,
                "final_recommendation": "Shortlist",
                "job_role": "Backend Engineer",
            }),
            deterministic_score=82,
            status="shortlisted",
            timestamp=datetime.now(timezone.utc),
        )
        db.add(result)
        db.commit()

        hub = build_analytics_hub(db, user.tenant_id, period="last_30_days", slices=["screening"])
        row = hub["slices"]["screening"]["drill_down"][0]

        assert row["candidate_name"] == "Jane Doe"
        assert row["candidate_email"] == "jane@example.com"
        assert row["requisition_title"] == "Backend Engineer"
        assert row["recommendation"] == "Shortlist"
        assert row["result_id"] == result.id
        assert "trends" in hub["slices"]["screening"]
        assert hub["slices"]["screening"]["kpis"]["pipeline_shortlist_rate"] == 100.0

    def test_drill_down_falls_back_to_analysis_contact_name(self, db, auth_client):
        user = _admin_user(db)
        cand = Candidate(tenant_id=user.tenant_id, name=None, email=None)
        db.add(cand)
        db.flush()

        result = ScreeningResult(
            tenant_id=user.tenant_id,
            candidate_id=cand.id,
            resume_text="Resume text",
            jd_text="Long enough job description for testing candidate name fallback.",
            parsed_data=json.dumps({"contact_info": {"name": "Revanth Kumar", "email": "revanth@example.com"}}),
            analysis_result=json.dumps({
                "fit_score": 74,
                "final_recommendation": "Consider",
                "contact_info": {"name": "Revanth Kumar", "email": "revanth@example.com"},
            }),
            deterministic_score=74,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(result)
        db.commit()

        hub = build_analytics_hub(db, user.tenant_id, period="last_30_days", slices=["screening"])
        row = hub["slices"]["screening"]["drill_down"][0]
        assert row["candidate_name"] == "Revanth Kumar"
        assert row["candidate_email"] == "revanth@example.com"
        assert row["recommendation"] == "Consider"

    def test_hub_endpoint(self, auth_client_with_agency_plan):
        resp = auth_client_with_agency_plan.get("/api/analytics/hub?period=last_30_days&slices=screening")
        assert resp.status_code == 200
        data = resp.json()
        assert "slices" in data
        assert "screening" in data["slices"]
        assert "generated_at" in data

    def test_hub_plan_gating_403(self, auth_client):
        resp = auth_client.get("/api/analytics/hub?period=last_30_days")
        assert resp.status_code == 403

    def test_screening_endpoint_plan_gating_403(self, auth_client):
        resp = auth_client.get("/api/analytics/screening?period=last_30_days")
        assert resp.status_code == 403

    def test_invalid_period_rejected(self, auth_client_with_agency_plan):
        resp = auth_client_with_agency_plan.get("/api/analytics/hub?period=last_year")
        assert resp.status_code == 422

    def test_invalid_slice_rejected(self, auth_client_with_agency_plan):
        resp = auth_client_with_agency_plan.get("/api/analytics/hub?period=last_30_days&slices=invalid")
        assert resp.status_code == 400

    def test_cross_tenant_requisition_filter_404(self, auth_client_with_agency_plan):
        resp = auth_client_with_agency_plan.get(
            "/api/analytics/hub?period=last_30_days&requisition_id=999999991"
        )
        assert resp.status_code == 404

    def test_hm_submissions_respect_period(self, db, auth_client):
        user = _admin_user(db)
        req = Requisition(
            tenant_id=user.tenant_id,
            title="HM Period Test",
            jd_text="Job description for HM period testing long enough.",
            created_by=user.id,
        )
        db.add(req)
        db.flush()
        cand_old = Candidate(tenant_id=user.tenant_id, name="Old HM", email="old@example.com")
        cand_new = Candidate(tenant_id=user.tenant_id, name="New HM", email="new@example.com")
        db.add_all([cand_old, cand_new])
        db.flush()

        old = datetime.now(timezone.utc) - timedelta(days=60)
        recent = datetime.now(timezone.utc) - timedelta(days=2)

        db.add(RequisitionCandidate(
            requisition_id=req.id,
            candidate_id=cand_old.id,
            submission_status="reviewed",
            submitted_at=old,
            outcome_at=old,
            hm_outcome="approved",
        ))
        db.add(RequisitionCandidate(
            requisition_id=req.id,
            candidate_id=cand_new.id,
            submission_status="submitted",
            submitted_at=recent,
        ))
        db.commit()

        hub = build_analytics_hub(db, user.tenant_id, period="last_7_days", slices=["hm"])
        assert hub["slices"]["hm"]["submissions_sent"] == 1

    def test_screening_api_matches_hub_trends(self, db, auth_client):
        user = _admin_user(db)
        result = ScreeningResult(
            tenant_id=user.tenant_id,
            resume_text="Resume",
            jd_text="Job description long enough for screening analytics parity test.",
            parsed_data="{}",
            analysis_result=json.dumps({"fit_score": 88, "final_recommendation": "Shortlist"}),
            deterministic_score=88,
            status="shortlisted",
            timestamp=datetime.now(timezone.utc),
        )
        db.add(result)
        db.commit()

        screening = build_screening_analytics(db, user.tenant_id, period="last_30_days")
        hub = build_analytics_hub(db, user.tenant_id, period="last_30_days", slices=["screening"])
        trends = hub["slices"]["screening"]["trends"]
        assert screening["total_analyzed"] == trends["total_analyzed"]
        assert screening["avg_fit_score"] == trends["avg_fit_score"]
        assert screening["pipeline_shortlist_rate"] == trends["pipeline_shortlist_rate"]

    def test_lazy_slices_only_loads_requested(self, db, auth_client):
        user = _admin_user(db)
        hub = build_analytics_hub(db, user.tenant_id, period="last_30_days", slices=["team"])
        assert "team" in hub["slices"]
        assert "screening" not in hub["slices"]

    def test_viewer_masks_email(self, db, auth_client):
        user = _admin_user(db)
        cand = Candidate(tenant_id=user.tenant_id, name="Masked", email="secret@example.com")
        db.add(cand)
        db.flush()
        db.add(ScreeningResult(
            tenant_id=user.tenant_id,
            candidate_id=cand.id,
            resume_text="Resume",
            jd_text="Job description long enough for PII mask test case.",
            parsed_data="{}",
            analysis_result=json.dumps({"fit_score": 70, "final_recommendation": "Consider"}),
            deterministic_score=70,
            timestamp=datetime.now(timezone.utc),
        ))
        db.commit()
        hub = build_analytics_hub(
            db, user.tenant_id, period="last_30_days", slices=["screening"], include_pii=False
        )
        row = hub["slices"]["screening"]["drill_down"][0]
        assert row["candidate_email"] != "secret@example.com"
        assert "@" in row["candidate_email"]
