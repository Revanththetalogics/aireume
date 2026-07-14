"""Tests for analytics phases: overview, views, custom reports, metrics."""
from app.backend.models.db_models import SavedReport, User
from app.backend.services.analytics_metrics_service import get_metric_glossary
from app.backend.services.analytics_overview_service import build_analytics_overview
from app.backend.services.analytics_views_service import create_view, list_views
from app.backend.services.custom_report_service import (
    get_field_catalog,
    run_custom_report,
    create_saved_report,
    share_saved_report,
)


def _admin_user(db, auth_client=None):
    user = db.query(User).filter(User.email == "admin@testcorp.com").first()
    if not user:
        user = db.query(User).filter(User.email == "agency@agencycorp.com").first()
    return user


class TestAnalyticsOverview:
    def test_overview_returns_role_kpis(self, db, auth_client):
        user = _admin_user(db)
        assert user is not None
        payload = build_analytics_overview(db, user.tenant_id, user_role=user.role)
        assert "role_kpis" in payload
        assert "attention" in payload
        assert "default_slice" in payload
        assert payload["default_slice"] == "screening"

    def test_overview_api(self, auth_client_with_agency_plan):
        res = auth_client_with_agency_plan.get("/api/analytics/overview?period=last_30_days")
        assert res.status_code == 200
        data = res.json()
        assert "mini_trend" in data


class TestAnalyticsViews:
    def test_create_and_list_view(self, db, auth_client):
        user = _admin_user(db)
        assert user is not None
        created = create_view(
            db,
            user.tenant_id,
            user.id,
            name="My funnel view",
            view_type="explore",
            slice="funnel",
            filters={"period": "last_7_days"},
            is_default=True,
        )
        db.commit()
        views = list_views(db, user.tenant_id, user.id)
        assert any(v["id"] == created["id"] for v in views)
        assert any(v["is_default"] for v in views)

    def test_views_api(self, auth_client_with_agency_plan):
        res = auth_client_with_agency_plan.post("/api/analytics/views", json={
            "name": "API view",
            "view_type": "overview",
            "filters": {"period": "last_30_days"},
        })
        assert res.status_code == 200
        listed = auth_client_with_agency_plan.get("/api/analytics/views")
        assert listed.status_code == 200
        assert len(listed.json()["views"]) >= 1


class TestCustomReports:
    def test_field_catalog(self):
        catalog = get_field_catalog()
        assert "entities" in catalog
        assert "requisition_candidates" in catalog["entities"]

    def test_run_custom_report_pipeline(self, db, auth_client):
        user = _admin_user(db)
        assert user is not None
        result = run_custom_report(
            db,
            user.tenant_id,
            {
                "entity": "requisition_candidates",
                "columns": ["requisition_title", "pipeline_status"],
                "period": "last_90_days",
            },
        )
        assert "rows" in result
        assert result["entity"] == "requisition_candidates"

    def test_group_by_report(self, db, auth_client):
        user = _admin_user(db)
        assert user is not None
        result = run_custom_report(
            db,
            user.tenant_id,
            {
                "entity": "requisition_candidates",
                "group_by": ["pipeline_status"],
                "period": "last_90_days",
            },
        )
        assert result.get("group_by") == ["pipeline_status"]
        if result["rows"]:
            assert "row_count" in result["rows"][0]

    def test_saved_report_share(self, db, auth_client):
        user = _admin_user(db)
        assert user is not None
        saved = create_saved_report(
            db,
            user.tenant_id,
            user.id,
            name="Pipeline export",
            definition={"entity": "requisition_candidates", "period": "last_30_days"},
        )
        shared = share_saved_report(db, user.tenant_id, user.id, saved["id"])
        db.commit()
        assert shared["shared_with_tenant"] is True
        assert shared["share_token"]

    def test_custom_report_api(self, auth_client_with_agency_plan):
        res = auth_client_with_agency_plan.get("/api/analytics/reports/fields")
        assert res.status_code == 200
        run = auth_client_with_agency_plan.post("/api/analytics/reports/custom/run", json={
            "definition": {
                "entity": "requisitions",
                "period": "last_90_days",
            },
            "format": "json",
        })
        assert run.status_code == 200
        assert "rows" in run.json()


class TestAnalyticsMetrics:
    def test_glossary(self):
        data = get_metric_glossary()
        assert len(data["metrics"]) >= 5
        keys = {m["key"] for m in data["metrics"]}
        assert "recommendation_shortlist_rate" in keys
        assert "pipeline_shortlist_rate" in keys

    def test_metrics_api(self, auth_client_with_agency_plan):
        res = auth_client_with_agency_plan.get("/api/analytics/metrics")
        assert res.status_code == 200
        assert "metrics" in res.json()

    def test_bi_manifest_has_new_endpoints(self, auth_client_with_agency_plan):
        res = auth_client_with_agency_plan.get("/api/analytics/reports/bi-manifest")
        assert res.status_code == 200
        endpoints = res.json()["export_endpoints"]
        assert "overview" in endpoints
        assert "report_custom" in endpoints
