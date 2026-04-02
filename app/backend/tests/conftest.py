import sys
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.backend.db.database import Base, get_db
from app.backend.main import app

# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


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
January 2020 – Present
- Led development of microservices architecture
- Managed team of 5 engineers

Software Engineer | StartupXYZ
June 2017 – December 2019
- Built React frontend and Node.js backend
- Implemented CI/CD pipelines

Junior Developer | SmallCo
March 2015 – May 2017
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

The ideal candidate will have leadership experience and be comfortable
working in a fast-paced startup environment.
"""
