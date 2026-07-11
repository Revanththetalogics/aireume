"""Tests for analytics hub aggregates."""
from datetime import datetime, timedelta, timezone

from app.backend.models.db_models import UsageLog, User
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

    def test_hub_endpoint(self, auth_client):
        resp = auth_client.get("/api/analytics/hub?period=last_30_days")
        assert resp.status_code == 200
        data = resp.json()
        assert "slices" in data
        assert "screening" in data["slices"]
