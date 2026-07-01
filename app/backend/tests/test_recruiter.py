"""Tests for AI Recruiter feature."""
import json
import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone


class TestRecruiterRoutes:
    """Test recruiter API endpoints."""

    @patch("app.backend.services.recruiter.strategy_agent.InterviewStrategyAgent.generate_strategy", new_callable=AsyncMock)
    @patch("app.backend.services.voice_call_scheduler.schedule_voice_call")
    def test_create_session(self, mock_schedule, mock_strategy, client, auth_headers, sample_candidate, sample_jd):
        """Test initiating a recruiter interview."""
        mock_strategy.return_value = {
            "duration_minutes": 20,
            "questions": [
                {
                    "sequence_number": 1,
                    "category": "technical",
                    "question_text": "Tell me about your Python experience.",
                    "question_context": "Assess Python depth.",
                }
            ],
        }

        response = client.post("/api/recruiter/sessions", json={
            "candidate_id": sample_candidate.id,
            "jd_id": sample_jd.id,
            "trigger_type": "manual",
        }, headers=auth_headers)
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["status"] == "scheduled"
        assert data["trigger_type"] == "manual"
        assert data["candidate_id"] == sample_candidate.id
        assert data["jd_id"] == sample_jd.id

    def test_list_sessions(self, client, auth_headers):
        """Test listing recruiter sessions with pagination."""
        response = client.get("/api/recruiter/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_list_sessions_filter_by_status(self, client, auth_headers, recruiter_session):
        """Test filtering sessions by status."""
        response = client.get("/api/recruiter/sessions?status=pending_strategy", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) >= 1

    def test_get_session_detail(self, client, auth_headers, recruiter_session):
        """Test getting session detail."""
        response = client.get(f"/api/recruiter/sessions/{recruiter_session.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == recruiter_session.id

    def test_get_session_not_found(self, client, auth_headers):
        """Test 404 for nonexistent session."""
        response = client.get("/api/recruiter/sessions/nonexistent-uuid", headers=auth_headers)
        assert response.status_code == 404

    def test_get_transcript(self, client, auth_headers, recruiter_session_with_questions):
        """Test getting session transcript."""
        session = recruiter_session_with_questions
        response = client.get(f"/api/recruiter/sessions/{session.id}/transcript", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) == 1

    def test_get_scorecard(self, client, auth_headers, recruiter_session_with_scorecard):
        """Test getting scorecard."""
        session = recruiter_session_with_scorecard
        response = client.get(f"/api/recruiter/sessions/{session.id}/scorecard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 80
        assert data["recommendation"] == "hire"

    def test_cancel_session(self, client, auth_headers, recruiter_session):
        """Test cancelling a scheduled session."""
        response = client.post(f"/api/recruiter/sessions/{recruiter_session.id}/cancel", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancel_completed_session_fails(self, client, auth_headers, completed_recruiter_session):
        """Test that completed sessions cannot be cancelled."""
        response = client.post(f"/api/recruiter/sessions/{completed_recruiter_session.id}/cancel", headers=auth_headers)
        assert response.status_code == 400

    def test_get_config(self, client, admin_auth_headers):
        """Test getting auto-trigger config."""
        response = client.get("/api/recruiter/config", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "trigger_pipeline_stage" in data

    def test_update_config(self, client, admin_auth_headers):
        """Test updating auto-trigger config."""
        response = client.put("/api/recruiter/config", json={
            "enabled": True,
            "trigger_pipeline_stage": "shortlisted",
            "min_fit_score_threshold": 50,
            "max_fit_score_threshold": 90,
        }, headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["trigger_pipeline_stage"] == "shortlisted"
        assert data["min_fit_score_threshold"] == 50
        assert data["max_fit_score_threshold"] == 90

    def test_config_requires_admin(self, client, auth_headers):
        """Test that config endpoints require admin role."""
        response = client.put("/api/recruiter/config", json={
            "enabled": True
        }, headers=auth_headers)
        assert response.status_code == 403

    def test_analytics(self, client, auth_headers):
        """Test analytics endpoint."""
        response = client.get("/api/recruiter/analytics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data

    def test_tenant_isolation(self, client, auth_headers, other_tenant_session):
        """Test that sessions from other tenants are not visible."""
        response = client.get(f"/api/recruiter/sessions/{other_tenant_session.id}", headers=auth_headers)
        assert response.status_code == 404


class TestContextEngine:
    """Test InterviewContextEngine."""

    def test_build_context(self, db_session, sample_candidate, sample_screening_result, sample_jd):
        """Test context building aggregates all data."""
        from app.backend.services.recruiter.context_engine import InterviewContextEngine
        engine = InterviewContextEngine()
        context = engine.build_context(
            db_session,
            sample_candidate.id,
            sample_screening_result.id,
            sample_jd.id,
        )

        assert "candidate" in context
        assert "role" in context
        assert "screening_result" in context
        assert "skill_match" in context
        assert "probe_areas" in context

    def test_identify_probe_areas(self):
        """Test probe area identification."""
        from app.backend.services.recruiter.context_engine import InterviewContextEngine
        engine = InterviewContextEngine()

        context = {
            "candidate": {
                "parsed_skills": ["python", "java"],
                "gap_analysis": {"gaps": [{"duration_months": 8}]},
                "parsed_work_experience": [
                    {"title": "Software Engineer"},
                    {"title": "Data Scientist"},
                ],
            },
            "role": {"required_skills": ["python", "kubernetes", "aws"]},
            "screening_result": {
                "fit_score": 65,
                "risk_signals": [{"type": "job_hopping", "description": "Frequent moves"}],
                "analysis_result": {"skills": 40},
            },
            "skill_match": {"matched": ["python"], "gaps": ["kubernetes", "aws"]},
        }

        probe_areas = engine.identify_probe_areas(context)
        assert len(probe_areas) > 0
        categories = [p.get("category") for p in probe_areas]
        assert "skill_validation" in categories
        assert "employment_gap" in categories
        assert "risk_validation" in categories


class TestAutoTrigger:
    """Test auto-trigger logic."""

    @pytest.mark.asyncio
    async def test_trigger_conditions_met(self, db_session, sample_candidate, sample_screening_result):
        """Test that trigger fires when all conditions are met."""
        from app.backend.services.recruiter.auto_trigger import RecruiterAutoTrigger
        from app.backend.models.db_models import RecruiterAutoTriggerConfig

        config = RecruiterAutoTriggerConfig(
            id=str(uuid.uuid4()),
            tenant_id=sample_candidate.tenant_id,
            enabled=True,
            trigger_pipeline_stage="shortlisted",
            min_fit_score_threshold=40,
            max_fit_score_threshold=85,
        )
        db_session.add(config)
        db_session.commit()

        trigger = RecruiterAutoTrigger(db_session)

        with patch("app.backend.services.recruiter.orchestrator.RecruiterOrchestrator.initiate_interview", new_callable=AsyncMock) as mock_init:
            mock_init.return_value = "test-session-id"

            result = await trigger.evaluate_trigger(
                tenant_id=sample_candidate.tenant_id,
                candidate_id=sample_candidate.id,
                screening_result_id=sample_screening_result.id,
                new_status="shortlisted",
            )

            assert result is True
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_disabled(self, db_session, sample_candidate, sample_screening_result):
        """Test that disabled trigger does not fire."""
        from app.backend.services.recruiter.auto_trigger import RecruiterAutoTrigger

        trigger = RecruiterAutoTrigger(db_session)
        result = await trigger.evaluate_trigger(
            tenant_id=sample_candidate.tenant_id,
            candidate_id=sample_candidate.id,
            screening_result_id=sample_screening_result.id,
            new_status="shortlisted",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_trigger_score_below_threshold(self, db_session, sample_candidate, sample_screening_result):
        """Test trigger skips low-score candidates."""
        from app.backend.services.recruiter.auto_trigger import RecruiterAutoTrigger
        from app.backend.models.db_models import RecruiterAutoTriggerConfig

        config = RecruiterAutoTriggerConfig(
            id=str(uuid.uuid4()),
            tenant_id=sample_candidate.tenant_id,
            enabled=True,
            trigger_pipeline_stage="shortlisted",
            min_fit_score_threshold=70,
            max_fit_score_threshold=85,
        )
        db_session.add(config)
        db_session.commit()

        trigger = RecruiterAutoTrigger(db_session)
        result = await trigger.evaluate_trigger(
            tenant_id=sample_candidate.tenant_id,
            candidate_id=sample_candidate.id,
            screening_result_id=sample_screening_result.id,
            new_status="shortlisted",
        )
        assert result is False


class TestContextEngineGapFixes:
    """Tests for audit gap fixes in context_engine.py."""

    def test_extract_skill_match_uses_missing_skills_key(self):
        """GAP 2: _extract_skill_match should read missing_skills (not gap_skills)."""
        from app.backend.services.recruiter.context_engine import InterviewContextEngine
        engine = InterviewContextEngine()

        screening = MagicMock()
        screening.analysis_result = json.dumps({
            "matched_skills": ["python", "java"],
            "missing_skills": ["kubernetes", "aws", "docker"],
            "gap_skills": ["old_key_should_not_be_used"],
        })
        screening.core_skill_score = 75.0

        result = engine._extract_skill_match(screening)
        assert result["gaps"] == ["kubernetes", "aws", "docker"]
        assert "old_key_should_not_be_used" not in result["gaps"]

    def test_extract_skill_match_falls_back_to_gap_skills(self):
        """GAP 2: backward compatibility — fall back to gap_skills when missing_skills absent."""
        from app.backend.services.recruiter.context_engine import InterviewContextEngine
        engine = InterviewContextEngine()

        screening = MagicMock()
        screening.analysis_result = json.dumps({
            "matched_skills": ["python"],
            "gap_skills": ["kubernetes"],
        })
        screening.core_skill_score = 70.0

        result = engine._extract_skill_match(screening)
        assert result["gaps"] == ["kubernetes"]

    def test_find_weak_dimensions_reads_score_breakdown(self):
        """GAP 3: _find_weak_dimensions should read from score_breakdown nested dict."""
        from app.backend.services.recruiter.context_engine import InterviewContextEngine
        engine = InterviewContextEngine()

        screening = {
            "analysis_result": {
                "score_breakdown": {
                    "skill_match": {"score": 35},
                    "experience_match": {"score": 60},
                    "education": 25,
                    "domain_fit": 45,
                    "architecture": 80,
                    "stability": 90,
                }
            }
        }

        weak = engine._find_weak_dimensions(screening)
        weak_dims = [d for d, s in weak]
        assert "skills" in weak_dims
        assert "education" in weak_dims
        assert "domain_fit" in weak_dims
        assert "experience" not in weak_dims
        assert "architecture" not in weak_dims
        assert "stability" not in weak_dims

    def test_find_weak_dimensions_empty_when_no_score_breakdown(self):
        """GAP 3: returns empty list when score_breakdown is absent."""
        from app.backend.services.recruiter.context_engine import InterviewContextEngine
        engine = InterviewContextEngine()

        screening = {"analysis_result": {"skills": 30, "experience": 20}}
        weak = engine._find_weak_dimensions(screening)
        assert weak == []

    def test_find_weak_dimensions_handles_dict_and_raw_values(self):
        """GAP 3: should handle both dict-wrapped and raw number score_breakdown values."""
        from app.backend.services.recruiter.context_engine import InterviewContextEngine
        engine = InterviewContextEngine()

        screening = {
            "analysis_result": {
                "score_breakdown": {
                    "skill_match": {"score": 30},
                    "education": 40,
                    "architecture": {"score": 55},
                }
            }
        }

        weak = engine._find_weak_dimensions(screening)
        weak_dims = {d: s for d, s in weak}
        assert weak_dims["skills"] == 30
        assert weak_dims["education"] == 40
        assert "architecture" not in weak_dims

    def test_screening_data_uses_deterministic_score_column(self, db_session, sample_candidate, sample_screening_result, sample_jd):
        """GAP 4: _extract_screening_data should read deterministic_score from DB column."""
        from app.backend.services.recruiter.context_engine import InterviewContextEngine
        engine = InterviewContextEngine()

        data = engine._extract_screening_data(sample_screening_result)
        assert data["fit_score"] == 65
        assert data["core_skill_score"] == 70.0
