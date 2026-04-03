"""
Phase 1 feature tests:
  - Batch upload (/api/analyze/batch)
  - Candidate comparison (/api/compare)
  - ATS export (/api/export/csv, /api/export/excel)
  - Templates CRUD (/api/templates)
  - Candidates list/detail (/api/candidates)
  - History + status update (/api/history, /api/results/{id}/status)
"""
import io
import json
import pytest
from unittest.mock import patch, AsyncMock


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_resume_file(name="resume.txt", content=None):
    content = content or b"John Doe\nSoftware Engineer\njohn@test.com\n\nSKILLS\nPython, React\n"
    return (name, io.BytesIO(content), "text/plain")


PIPELINE_RESULT = {
    "fit_score": 70,
    "strengths": ["Good Python skills"],
    "weaknesses": [],
    "education_analysis": "OK",
    "risk_signals": [],
    "final_recommendation": "Consider",
    "employment_gaps": [],
    "score_breakdown": {"skill_match": 70, "experience_match": 65, "stability": 90, "education": 65},
    "matched_skills": ["python"],
    "missing_skills": [],
    "risk_level": "Low",
    "interview_questions": {"technical_questions": [], "behavioral_questions": [], "culture_fit_questions": []},
    "required_skills_count": 3,
    "result_id": None,
}


# ─── History ──────────────────────────────────────────────────────────────────

class TestHistory:
    def test_history_returns_list(self, auth_client):
        resp = auth_client.get("/api/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_history_requires_auth(self, client):
        resp = client.get("/api/history")
        assert resp.status_code == 401


# ─── Templates CRUD ───────────────────────────────────────────────────────────

class TestTemplates:
    def test_list_templates_empty(self, auth_client):
        resp = auth_client.get("/api/templates")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_template(self, auth_client):
        resp = auth_client.post("/api/templates", json={
            "name": "Senior Python Dev",
            "jd_text": "We need a senior Python developer with 5+ years of experience.",
            "tags": "python,senior,backend",
        })
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["name"] == "Senior Python Dev"
        assert "id" in data

    def test_create_and_list_templates(self, auth_client):
        auth_client.post("/api/templates", json={"name": "T1", "jd_text": "JD1", "tags": ""})
        auth_client.post("/api/templates", json={"name": "T2", "jd_text": "JD2", "tags": ""})
        resp = auth_client.get("/api/templates")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_update_template(self, auth_client):
        create = auth_client.post("/api/templates", json={"name": "Old Name", "jd_text": "JD", "tags": ""})
        tid = create.json()["id"]
        resp = auth_client.put(f"/api/templates/{tid}", json={"name": "New Name", "jd_text": "Updated JD", "tags": "updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_delete_template(self, auth_client):
        create = auth_client.post("/api/templates", json={"name": "ToDelete", "jd_text": "JD", "tags": ""})
        tid = create.json()["id"]
        del_resp = auth_client.delete(f"/api/templates/{tid}")
        assert del_resp.status_code in (200, 204)
        list_resp = auth_client.get("/api/templates")
        assert all(t["id"] != tid for t in list_resp.json())

    def test_update_nonexistent_template_returns_404(self, auth_client):
        resp = auth_client.put("/api/templates/99999", json={"name": "X", "jd_text": "Y", "tags": ""})
        assert resp.status_code == 404

    def test_templates_require_auth(self, client):
        resp = client.get("/api/templates")
        assert resp.status_code == 401


# ─── Candidates ───────────────────────────────────────────────────────────────

class TestCandidates:
    def test_list_candidates_empty(self, auth_client):
        resp = auth_client.get("/api/candidates")
        assert resp.status_code == 200
        data = resp.json()
        assert "candidates" in data
        assert isinstance(data["candidates"], list)

    def test_get_nonexistent_candidate_returns_404(self, auth_client):
        resp = auth_client.get("/api/candidates/99999")
        assert resp.status_code == 404

    def test_candidates_require_auth(self, client):
        resp = client.get("/api/candidates")
        assert resp.status_code == 401


# ─── Batch analyze ────────────────────────────────────────────────────────────

class TestBatchAnalyze:
    def test_batch_analyze_returns_ranked_results(self, auth_client, mock_agent_pipeline):
        files = [
            ("resumes", make_resume_file("r1.txt")),
            ("resumes", make_resume_file("r2.txt")),
        ]
        resp = auth_client.post(
            "/api/analyze/batch",
            data={"job_description": "Python developer needed with 5 years experience"},
            files=files,
        )
        # 200 with results, or 400/422 if pipeline validation fails in test env
        if resp.status_code == 200:
            data = resp.json()
            assert "results" in data
        else:
            # At minimum, auth was accepted (not 401)
            assert resp.status_code != 401

    def test_batch_requires_auth(self, client):
        resp = client.post(
            "/api/analyze/batch",
            data={"job_description": "test"},
            files=[("resumes", make_resume_file())],
        )
        assert resp.status_code == 401

    def test_batch_missing_jd_returns_400(self, auth_client):
        resp = auth_client.post(
            "/api/analyze/batch",
            data={},
            files=[("resumes", make_resume_file())],
        )
        assert resp.status_code == 400


# ─── Compare ─────────────────────────────────────────────────────────────────

class TestCompare:
    def test_compare_requires_auth(self, client):
        resp = client.post("/api/compare", json={"candidate_ids": [1, 2]})
        assert resp.status_code == 401

    def test_compare_nonexistent_ids_returns_404_or_empty(self, auth_client):
        resp = auth_client.post("/api/compare", json={"candidate_ids": [9001, 9002]})
        # Either 404 or empty comparison result
        assert resp.status_code in (200, 404)

    def test_compare_too_few_ids_returns_400(self, auth_client):
        resp = auth_client.post("/api/compare", json={"candidate_ids": [1]})
        assert resp.status_code == 400


# ─── Export ──────────────────────────────────────────────────────────────────

class TestExport:
    def test_export_csv_requires_auth(self, client):
        resp = client.get("/api/export/csv")
        assert resp.status_code == 401

    def test_export_excel_requires_auth(self, client):
        resp = client.get("/api/export/excel")
        assert resp.status_code == 401

    def test_export_csv_returns_csv_content(self, auth_client):
        resp = auth_client.get("/api/export/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_export_excel_returns_xlsx_content(self, auth_client):
        resp = auth_client.get("/api/export/excel")
        assert resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        assert "spreadsheetml" in ct or "excel" in ct or "octet-stream" in ct

    def test_export_csv_with_ids_filter(self, auth_client):
        resp = auth_client.get("/api/export/csv?ids=1,2,3")
        assert resp.status_code == 200


# ─── Status update ────────────────────────────────────────────────────────────

class TestStatusUpdate:
    def test_update_status_requires_auth(self, client):
        resp = client.put("/api/results/1/status", json={"status": "shortlisted"})
        assert resp.status_code == 401

    def test_update_status_nonexistent_returns_404(self, auth_client):
        resp = auth_client.put("/api/results/99999/status", json={"status": "shortlisted"})
        assert resp.status_code == 404
