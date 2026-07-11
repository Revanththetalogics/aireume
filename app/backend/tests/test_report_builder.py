"""Tests for report builder exports."""
import base64

from app.backend.services.report_builder_service import run_report, _to_xlsx


def _admin_user(db):
    from app.backend.models.db_models import User
    return db.query(User).filter(User.email == "admin@testcorp.com").first()


class TestReportBuilder:
    def test_xlsx_export(self, db, auth_client):
        user = _admin_user(db)
        assert user is not None
        payload = run_report(
            db,
            user.tenant_id,
            template_id="screening_volume",
            period="last_30_days",
            format="xlsx",
        )
        assert "xlsx_base64" in payload
        raw = base64.b64decode(payload["xlsx_base64"])
        assert raw[:2] == b"PK"

    def test_pipeline_detail_csv(self, db, auth_client):
        user = _admin_user(db)
        assert user is not None
        payload = run_report(
            db,
            user.tenant_id,
            template_id="candidate_pipeline_detail",
            period="last_90_days",
            format="csv",
        )
        assert "csv" in payload
