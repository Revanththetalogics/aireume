"""
Pytest fixtures shared across all backend test modules.
"""
import sys
import os
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, AsyncMock, MagicMock

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.backend.db import database
from app.backend.main import app

# ─── In-memory SQLite DB ──────────────────────────────────────────────────────

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # single shared in-memory DB for all connections
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


database.engine = test_engine
database.SessionLocal = TestingSessionLocal
app.dependency_overrides[database.get_db] = override_get_db

# ─── Patch bcrypt → sha256_crypt for local test compatibility ────────────────
# passlib 1.7.4 + bcrypt 4.x has a known incompatibility. Use sha256_crypt in
# tests (same API, no C-library issues, not for production).
try:
    from passlib.context import CryptContext as _CC
    import app.backend.routes.auth as _auth_mod
    _auth_mod.pwd_context = _CC(schemes=["sha256_crypt"], deprecated="auto")
except Exception:
    pass  # If patching fails, fall through and let tests error naturally


# ─── Base fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db():
    database.Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        database.Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client():
    database.Base.metadata.create_all(bind=test_engine)
    with TestClient(app) as c:
        yield c
    database.Base.metadata.drop_all(bind=test_engine)


# ─── Authenticated client fixture ────────────────────────────────────────────

@pytest.fixture(scope="function")
def auth_client(client):
    """
    Returns a TestClient already configured with a valid JWT Bearer token.
    Registers a tenant + admin user, logs in, injects the Authorization header.
    """
    register_payload = {
        "company_name": "TestCorp",
        "email": "admin@testcorp.com",
        "password": "TestPass123!",
        "full_name": "Test Admin",
    }
    reg_resp = client.post("/api/auth/register", json=register_payload)
    assert reg_resp.status_code in (200, 201), f"Register failed: {reg_resp.text}"

    login_resp = client.post("/api/auth/login", json={
        "email": "admin@testcorp.com",
        "password": "TestPass123!",
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]

    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture(scope="function")
def auth_client_with_token(client):
    """
    Like auth_client but also returns the raw token for cases where tests need it.
    """
    register_payload = {
        "company_name": "TokenCorp",
        "email": "user@tokencorp.com",
        "password": "SecurePass456!",
        "full_name": "Token User",
    }
    client.post("/api/auth/register", json=register_payload)
    login_resp = client.post("/api/auth/login", json={
        "email": "user@tokencorp.com",
        "password": "SecurePass456!",
    })
    token = login_resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, token


# ─── Mock Ollama ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_ollama_communication():
    """Mock Ollama returning a valid communication analysis JSON."""
    response_body = json.dumps({
        "communication_score": 78,
        "confidence_level": "high",
        "clarity_score": 82,
        "articulation_score": 75,
        "key_phrases": ["strong technical background", "team player"],
        "strengths": ["Clear articulation", "Good pacing"],
        "red_flags": [],
        "summary": "Candidate communicates clearly and confidently.",
    })
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": response_body}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.backend.services.video_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_ollama_malpractice():
    """Mock Ollama returning a valid malpractice analysis JSON."""
    response_body = json.dumps({
        "malpractice_score": 15,
        "malpractice_risk": "low",
        "reliability_rating": "trustworthy",
        "flags": [],
        "positive_signals": ["Natural filler words present", "Self-corrections observed"],
        "overall_assessment": "No significant malpractice signals detected.",
        "follow_up_questions": [],
    })
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": response_body}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.backend.services.video_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_whisper():
    """Mock faster-whisper transcription."""
    def fake_transcribe(video_path: str) -> dict:
        return {
            "transcript": (
                "Hello, I have five years of experience in Python development. "
                "I worked at TechCorp where I led a team of three engineers. "
                "I am proficient in FastAPI, React, and PostgreSQL."
            ),
            "segments": [
                {"start": 0.0, "end": 3.5, "text": "Hello, I have five years of experience in Python development.", "avg_logprob": -0.3, "no_speech_prob": 0.01},
                {"start": 3.8, "end": 8.1, "text": "I worked at TechCorp where I led a team of three engineers.", "avg_logprob": -0.25, "no_speech_prob": 0.02},
                {"start": 8.5, "end": 12.0, "text": "I am proficient in FastAPI, React, and PostgreSQL.", "avg_logprob": -0.2, "no_speech_prob": 0.01},
            ],
            "language": "en",
            "duration_s": 12.0,
        }

    with patch("app.backend.services.video_service.transcribe_video", side_effect=fake_transcribe):
        yield fake_transcribe


@pytest.fixture
def mock_agent_pipeline():
    """Mock the full agent pipeline to avoid Ollama calls in analyze tests."""
    pipeline_result = {
        "fit_score": 75,
        "strengths": ["Strong Python skills", "Good communication"],
        "weaknesses": ["Limited cloud experience"],
        "education_analysis": "Solid CS background",
        "risk_signals": [],
        "final_recommendation": "Consider",
        "employment_gaps": [],
        "score_breakdown": {
            "skill_match": 80, "experience_match": 70, "stability": 90, "education": 70
        },
        "matched_skills": ["python", "react"],
        "missing_skills": ["kubernetes"],
        "risk_level": "Low",
        "interview_questions": {
            "technical_questions": ["Explain FastAPI dependency injection."],
            "behavioral_questions": ["Tell me about a challenging project."],
            "culture_fit_questions": ["How do you handle tight deadlines?"],
        },
        "required_skills_count": 5,
        "result_id": 1,
    }
    with patch("app.backend.routes.analyze.run_agent_pipeline", new_callable=AsyncMock) as mock:
        mock.return_value = pipeline_result
        yield mock


# ─── Sample data ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_resume_text():
    return """
John Doe
Software Engineer
john.doe@email.com | +1-555-123-4567 | linkedin.com/in/johndoe

SUMMARY
Experienced software engineer with 8 years in full-stack development.

SKILLS
Python, JavaScript, React, Node.js, PostgreSQL, AWS, Docker, Kubernetes

WORK EXPERIENCE

Senior Software Engineer | TechCorp Inc.
January 2020 - Present
- Led development of microservices architecture
- Managed team of 5 engineers

Software Engineer | StartupXYZ
June 2017 - December 2019
- Built React frontend and Node.js backend
- Implemented CI/CD pipelines

Junior Developer | SmallCo
March 2015 - May 2017
- Developed internal tools using Python
- Maintained legacy systems

EDUCATION
Bachelor of Science in Computer Science
University of Technology, 2015
"""


@pytest.fixture
def sample_job_description():
    return """
Senior Software Engineer

We are looking for an experienced software engineer with:
- 5+ years of Python experience
- Strong React and JavaScript skills
- Experience with cloud platforms (AWS/GCP)
- Knowledge of Docker and Kubernetes
- PostgreSQL database experience

The ideal candidate will have leadership experience.
"""


@pytest.fixture
def sample_resume_bytes(sample_resume_text):
    return sample_resume_text.encode("utf-8")


@pytest.fixture
def sample_mp4_bytes():
    """Minimal fake MP4 bytes (just enough to pass file extension checks)."""
    return b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 100


@pytest.fixture
def mock_ollama_email():
    """Mock Ollama returning a valid email JSON."""
    response_body = json.dumps({
        "subject": "Your Application — Senior Software Engineer",
        "body": "Dear John,\n\nCongratulations! We'd like to move forward.\n\nBest regards",
    })
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": response_body}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.backend.routes.email_gen.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client
        yield mock_client
