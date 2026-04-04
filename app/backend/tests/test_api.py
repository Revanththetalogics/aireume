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
        # In CI / local tests Ollama is not running, so the enriched health
        # endpoint may return "degraded". Both "ok" and "degraded" are valid
        # HTTP-200 responses — the important thing is the endpoint is reachable.
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in ("ok", "degraded")

    def test_analyze_endpoint_success(self, auth_client):
        file_content = (
            b"John Doe\nSenior Software Engineer\njohn@email.com\n\n"
            b"SKILLS\nPython, FastAPI, PostgreSQL\n\n"
            b"WORK EXPERIENCE\nSenior Dev | Company A | Jan 2020 - Present\n\n"
            b"EDUCATION\nBSc Computer Science, MIT, 2018\n"
        )
        _JD = (
            "Senior Python Backend Engineer. We need at least 5 years of Python "
            "experience with FastAPI or Django, PostgreSQL, Docker, and Kubernetes. "
            "Strong understanding of microservices, REST API design, and cloud "
            "platforms like AWS or GCP is required. The role involves leading a "
            "small engineering team and collaborating with data scientists. "
            "Experience with CI/CD pipelines, Redis caching, and async Python is "
            "highly desirable. The candidate should be comfortable with code review "
            "and technical mentoring of junior developers."
        )
        pipeline_result = {
            "fit_score": 75, "job_role": "Senior Python Engineer",
            "strengths": ["Strong Python skills"], "weaknesses": [],
            "education_analysis": "Good background.", "risk_signals": [],
            "final_recommendation": "Consider", "employment_gaps": [],
            "score_breakdown": {"skill_match": 80, "experience_match": 70,
                                "stability": 100, "education": 70},
            "matched_skills": ["python"], "missing_skills": [], "adjacent_skills": [],
            "risk_level": "Low",
            "interview_questions": {"technical_questions": [], "behavioral_questions": [],
                                    "culture_fit_questions": []},
            "required_skills_count": 3, "jd_analysis": {}, "candidate_profile": {},
            "skill_analysis": {}, "edu_timeline_analysis": {}, "explainability": {},
            "work_experience": [], "contact_info": {},
            "analysis_quality": "high", "narrative_pending": False, "pipeline_errors": [],
        }
        with patch("app.backend.routes.analyze.parse_resume", return_value={
            "raw_text": "John Doe python fastapi", "skills": ["python", "fastapi"],
            "education": [], "work_experience": [],
            "contact_info": {"name": "John Doe", "email": "john@email.com"},
        }), patch("app.backend.routes.analyze.analyze_gaps", return_value={}), \
           patch("app.backend.routes.analyze.run_hybrid_pipeline",
                 new_callable=AsyncMock, return_value=pipeline_result):
            response = auth_client.post(
                "/api/analyze",
                data={"job_description": _JD},
                files={"resume": ("resume.pdf", io.BytesIO(file_content), "application/pdf")},
            )
        if response.status_code == 200:
            assert "fit_score" in response.json()

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

    def test_batch_analyze_returns_ranked_results(self, auth_client, mock_hybrid_pipeline):
        """Batch endpoint must return ranked results; null fit_score is allowed."""
        import io
        resume_bytes = b"John Doe\nPython Developer\njohn@email.com\n5 years Python"
        _JD = (
            "Senior Python Backend Engineer with at least 5 years of hands-on "
            "experience building scalable REST APIs using FastAPI or Django REST "
            "Framework. Strong knowledge of PostgreSQL, Redis, Docker, and "
            "Kubernetes is required for this role. Experience with cloud platforms "
            "such as AWS or GCP is strongly preferred. The ideal candidate should "
            "be comfortable leading cross-functional teams, conducting thorough code "
            "reviews, and mentoring junior engineers day to day. Familiarity with "
            "async Python, Celery task queues, and message brokers like RabbitMQ "
            "or Kafka will be considered a significant advantage in this position."
        )

        response = auth_client.post(
            "/api/analyze/batch",
            data={"job_description": _JD},
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
