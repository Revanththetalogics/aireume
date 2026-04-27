"""Tests for domain_service.py — domain detection from JD and resume."""

import pytest

from app.backend.services.domain_service import detect_domain_from_jd, detect_domain_from_resume


class TestDetectDomainFromJd:
    """Tests for detect_domain_from_jd."""

    def test_empty_string_returns_unknown(self):
        result = detect_domain_from_jd("")
        assert result["domain"] == "unknown"
        assert result["confidence"] == 0.0
        assert result["scores"] == {}

    def test_none_returns_unknown(self):
        result = detect_domain_from_jd(None)
        assert result["domain"] == "unknown"
        assert result["confidence"] == 0.0
        assert result["scores"] == {}

    def test_embedded_keywords_detects_embedded(self):
        jd = "Looking for firmware developer with rtos and microcontroller experience."
        result = detect_domain_from_jd(jd)
        assert result["domain"] == "embedded"
        assert result["confidence"] > 0.0
        assert "embedded" in result["scores"]

    def test_backend_keywords_detects_backend(self):
        jd = "Need backend engineer with django, spring, and api development skills."
        result = detect_domain_from_jd(jd)
        assert result["domain"] == "backend"
        assert result["confidence"] > 0.0
        assert "backend" in result["scores"]

    def test_data_keywords_detects_data_science(self):
        jd = "Seeking data analyst with etl, sql, data pipeline, and data analysis experience."
        result = detect_domain_from_jd(jd)
        assert result["domain"] == "data_science"
        assert result["confidence"] > 0.0
        assert "data_science" in result["scores"]

    def test_low_confidence_returns_unknown(self):
        jd = "general manager position"
        result = detect_domain_from_jd(jd)
        assert result["domain"] == "unknown"
        assert result["confidence"] < 0.1

    def test_returns_dict_shape(self):
        jd = "Senior Python developer with FastAPI and PostgreSQL."
        result = detect_domain_from_jd(jd)
        assert set(result.keys()) == {"domain", "confidence", "scores"}
        assert isinstance(result["domain"], str)
        assert isinstance(result["confidence"], float)
        assert isinstance(result["scores"], dict)


class TestDetectDomainFromResume:
    """Tests for detect_domain_from_resume."""

    def test_empty_inputs_returns_unknown(self):
        result = detect_domain_from_resume(skills=None, resume_text=None)
        assert result["domain"] == "unknown"
        assert result["confidence"] == 0.0
        assert result["scores"] == {}

    def test_empty_lists_returns_unknown(self):
        result = detect_domain_from_resume(skills=[], resume_text="")
        assert result["domain"] == "unknown"
        assert result["confidence"] == 0.0
        assert result["scores"] == {}

    def test_mixed_skills_picks_strongest_domain(self):
        skills = [
            "rtos", "firmware", "microcontroller",  # embedded (3 matches)
            "fastapi", "django", "spring", "rest api", "postgresql", "mysql", "redis", "microservices", "golang", "node.js",  # backend (12 matches)
        ]
        result = detect_domain_from_resume(skills=skills)
        assert result["domain"] == "backend"
        assert result["confidence"] > 0.0
        assert result["scores"]["backend"] > result["scores"]["embedded"]

    def test_resume_text_fallback(self):
        resume_text = "Experienced in react, vue.js, angular, and tailwind css."
        result = detect_domain_from_resume(skills=None, resume_text=resume_text)
        assert result["domain"] == "frontend"
        assert result["confidence"] > 0.0

    def test_confidence_above_zero_for_matches(self):
        skills = ["python", "pandas", "numpy", "etl", "sql"]
        result = detect_domain_from_resume(skills=skills)
        assert result["confidence"] > 0.0

    def test_low_confidence_returns_unknown(self):
        skills = ["communication", "leadership"]
        result = detect_domain_from_resume(skills=skills)
        assert result["domain"] == "unknown"
        assert result["confidence"] < 0.1

    def test_returns_same_dict_shape(self):
        skills = ["kubernetes", "docker", "terraform"]
        result = detect_domain_from_resume(skills=skills)
        assert set(result.keys()) == {"domain", "confidence", "scores"}
        assert isinstance(result["domain"], str)
        assert isinstance(result["confidence"], float)
        assert isinstance(result["scores"], dict)
