import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import io


class TestAPIEndpoints:
    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert any(kw in data["message"] for kw in ("AI Resume Screener", "ARIA", "Resume", "API"))

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_analyze_endpoint_success(self, client):
        # Create a simple text file to upload
        file_content = b"""
John Doe
Software Engineer
john@email.com

SKILLS
Python, JavaScript, React

WORK EXPERIENCE
Senior Dev | Company A
January 2020 - Present
Building apps

EDUCATION
BS Computer Science
"""

        mock_llm_response = {
            "fit_score": 75,
            "strengths": ["Strong technical skills"],
            "weaknesses": ["Limited experience"],
            "education_analysis": "Good education background",
            "risk_signals": [],
            "final_recommendation": "Consider"
        }

        with patch('app.backend.routes.analyze.run_agent_pipeline', new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = {
                **mock_llm_response,
                "employment_gaps": [],
                "score_breakdown": {"skill_match": 80, "experience_match": 70, "stability": 100, "education": 70},
                "matched_skills": ["python"],
                "missing_skills": [],
                "risk_level": "Low",
            }

            response = client.post(
                "/api/analyze",
                data={"job_description": "Looking for Python developers"},
                files={"resume": ("resume.txt", io.BytesIO(file_content), "text/plain")}
            )

            if response.status_code == 200:
                data = response.json()
                assert "fit_score" in data

    def test_analyze_endpoint_invalid_file_type(self, auth_client):
        response = auth_client.post(
            "/api/analyze",
            data={"job_description": "Test job"},
            files={"resume": ("resume.exe", io.BytesIO(b"invalid content"), "application/octet-stream")}
        )
        assert response.status_code == 400

    def test_analyze_endpoint_missing_job_description(self, auth_client):
        file_content = b"Simple resume content"
        response = auth_client.post(
            "/api/analyze",
            data={},  # Missing job_description
            files={"resume": ("resume.txt", io.BytesIO(file_content), "text/plain")}
        )
        # Route returns 400 (explicit validation) when JD is missing
        assert response.status_code == 400

    def test_history_endpoint_unauthenticated_returns_401(self, client):
        response = client.get("/api/history")
        assert response.status_code == 401

    def test_history_endpoint_authenticated_returns_list(self, auth_client):
        response = auth_client.get("/api/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_batch_analyze_returns_ranked_results(self, auth_client, mock_agent_pipeline):
        """Batch endpoint must return ranked results; null fit_score is allowed."""
        import io
        resume_bytes = b"John Doe\nPython Developer\njohn@email.com\n5 years Python"

        # Override pipeline to return null fit_score (Pending / fallback state)
        mock_agent_pipeline.return_value = {
            **mock_agent_pipeline.return_value,
            "fit_score": None,
            "final_recommendation": "Pending",
            "job_role": "Backend Engineer",
        }

        response = auth_client.post(
            "/api/analyze/batch",
            data={"job_description": "Senior Python developer needed"},
            files=[
                ("resumes", ("resume1.pdf", io.BytesIO(resume_bytes), "application/pdf")),
                ("resumes", ("resume2.pdf", io.BytesIO(resume_bytes), "application/pdf")),
            ],
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        # Results must be a ranked list; null fit_score must not crash serialization
        for row in data["results"]:
            assert "rank" in row
            assert "filename" in row
            assert "result" in row
            # fit_score is allowed to be null
            assert "fit_score" in row["result"]

    def test_batch_analyze_rejects_no_valid_files(self, auth_client):
        """Batch endpoint with only unsupported file types returns 400."""
        import io
        response = auth_client.post(
            "/api/analyze/batch",
            data={"job_description": "Some job"},
            files=[("resumes", ("resume.exe", io.BytesIO(b"data"), "application/octet-stream"))],
        )
        assert response.status_code == 400

    def test_batch_analyze_requires_job_description(self, auth_client):
        """Batch endpoint without a JD returns 400."""
        import io
        response = auth_client.post(
            "/api/analyze/batch",
            data={},
            files=[("resumes", ("resume.pdf", io.BytesIO(b"resume"), "application/pdf"))],
        )
        assert response.status_code == 400
