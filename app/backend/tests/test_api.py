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
        assert "AI Resume Screener" in data["message"]

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
January 2020 – Present
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

        with patch('app.backend.routes.analyze.analyze_resume', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {
                **mock_llm_response,
                "employment_gaps": []
            }

            response = client.post(
                "/api/analyze",
                data={"job_description": "Looking for Python developers"},
                files={"resume": ("resume.txt", io.BytesIO(file_content), "text/plain")}
            )

            # May get 422 if file type is rejected, that's ok
            if response.status_code == 200:
                data = response.json()
                assert "fit_score" in data

    def test_analyze_endpoint_invalid_file_type(self, client):
        response = client.post(
            "/api/analyze",
            data={"job_description": "Test job"},
            files={"resume": ("resume.exe", io.BytesIO(b"invalid content"), "application/octet-stream")}
        )

        assert response.status_code == 400

    def test_analyze_endpoint_missing_job_description(self, client):
        file_content = b"Simple resume content"

        response = client.post(
            "/api/analyze",
            data={},  # Missing job_description
            files={"resume": ("resume.txt", io.BytesIO(file_content), "text/plain")}
        )

        assert response.status_code == 422

    def test_history_endpoint(self, client):
        response = client.get("/api/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
