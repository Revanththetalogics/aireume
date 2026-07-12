"""Tests for analytics hub aggregates."""
import json
from datetime import datetime, timedelta, timezone

from app.backend.models.db_models import Candidate, Requisition, ScreeningResult, UsageLog, User
from app.backend.services.analytics_hub_service import build_analytics_hub


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

        hub = build_analytics_hub(db, user.tenant_id, period="last_30_days")
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
            timestamp=datetime.now(timezone.utc),
        )
        db.add(result)
        db.commit()

        hub = build_analytics_hub(db, user.tenant_id, period="last_30_days")
        row = hub["slices"]["screening"]["drill_down"][0]

        assert row["candidate_name"] == "Jane Doe"
        assert row["candidate_email"] == "jane@example.com"
        assert row["requisition_title"] == "Backend Engineer"
        assert row["recommendation"] == "Shortlist"
        assert row["result_id"] == result.id
        assert "filter_options" in hub
        assert "attention" in hub

    def test_hub_endpoint(self, auth_client_with_agency_plan):
        resp = auth_client_with_agency_plan.get("/api/analytics/hub?period=last_30_days")
        assert resp.status_code == 200
        data = resp.json()
        assert "slices" in data
        assert "screening" in data["slices"]
        assert "filter_options" in data
        assert "attention" in data
