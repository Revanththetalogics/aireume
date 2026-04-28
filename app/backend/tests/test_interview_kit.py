"""Tests for Interview Kit evaluation and scorecard API."""
import json
import pytest
from app.backend.models.db_models import (
    ScreeningResult, Tenant, User, InterviewEvaluation, OverallAssessment,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _create_test_result(db, tenant_id: int, analysis: dict = None, parsed: dict = None):
    """Insert a ScreeningResult and return it."""
    result = ScreeningResult(
        tenant_id=tenant_id,
        candidate_id=None,
        resume_text="test resume",
        jd_text="test jd",
        parsed_data=json.dumps(parsed or {}),
        analysis_result=json.dumps(analysis or {}),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def _get_auth_tenant_and_user(db, auth_client):
    """Return (tenant, user) for the currently authenticated client."""
    tenant = db.query(Tenant).first()
    user = db.query(User).filter(User.tenant_id == tenant.id).first()
    return tenant, user


# ─── Evaluation CRUD ──────────────────────────────────────────────────────────

class TestInterviewKitEvaluation:
    """Test evaluation CRUD endpoints."""

    def test_upsert_evaluation_create(self, auth_client, db):
        """Test creating a new evaluation."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)
        result = _create_test_result(db, tenant.id)

        resp = auth_client.put(
            f"/api/results/{result.id}/evaluations",
            json={
                "question_category": "technical",
                "question_index": 0,
                "rating": "strong",
                "notes": "Excellent answer",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["question_category"] == "technical"
        assert data["question_index"] == 0
        assert data["rating"] == "strong"
        assert data["notes"] == "Excellent answer"
        assert "id" in data

    def test_upsert_evaluation_update(self, auth_client, db):
        """Test updating an existing evaluation."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)
        result = _create_test_result(db, tenant.id)

        # Create
        auth_client.put(
            f"/api/results/{result.id}/evaluations",
            json={
                "question_category": "technical",
                "question_index": 0,
                "rating": "adequate",
                "notes": "Okay answer",
            },
        )

        # Update
        resp = auth_client.put(
            f"/api/results/{result.id}/evaluations",
            json={
                "question_category": "technical",
                "question_index": 0,
                "rating": "strong",
                "notes": "Actually great answer",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] == "strong"
        assert data["notes"] == "Actually great answer"

    def test_get_evaluations_empty(self, auth_client, db):
        """Test getting evaluations when none exist."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)
        result = _create_test_result(db, tenant.id)

        resp = auth_client.get(f"/api/results/{result.id}/evaluations")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_evaluations_with_data(self, auth_client, db):
        """Test getting evaluations after creating some."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)
        result = _create_test_result(db, tenant.id)

        # Create two evaluations
        auth_client.put(
            f"/api/results/{result.id}/evaluations",
            json={"question_category": "technical", "question_index": 0, "rating": "strong"},
        )
        auth_client.put(
            f"/api/results/{result.id}/evaluations",
            json={"question_category": "behavioral", "question_index": 1, "rating": "weak", "notes": "Vague"},
        )

        resp = auth_client.get(f"/api/results/{result.id}/evaluations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Ordered by category then index
        assert data[0]["question_category"] == "behavioral"
        assert data[1]["question_category"] == "technical"

    def test_evaluation_tenant_isolation(self, auth_client, db):
        """Test that evaluations respect tenant boundaries."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)

        # Create result for a DIFFERENT tenant
        other_tenant = Tenant(name="Other Corp", slug="other-corp-eval")
        db.add(other_tenant)
        db.commit()
        db.refresh(other_tenant)

        result = _create_test_result(db, other_tenant.id)

        # Try to access — should be denied
        resp = auth_client.put(
            f"/api/results/{result.id}/evaluations",
            json={"question_category": "technical", "question_index": 0, "rating": "strong"},
        )
        assert resp.status_code == 403

        resp = auth_client.get(f"/api/results/{result.id}/evaluations")
        assert resp.status_code == 403

    def test_evaluation_category_validation(self, auth_client, db):
        """Test that invalid categories are rejected with 422."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)
        result = _create_test_result(db, tenant.id)

        resp = auth_client.put(
            f"/api/results/{result.id}/evaluations",
            json={"question_category": "invalid_category", "question_index": 0, "rating": "strong"},
        )
        assert resp.status_code == 422

    def test_evaluation_rating_validation(self, auth_client, db):
        """Test that invalid ratings are rejected with 422."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)
        result = _create_test_result(db, tenant.id)

        resp = auth_client.put(
            f"/api/results/{result.id}/evaluations",
            json={"question_category": "technical", "question_index": 0, "rating": "amazing"},
        )
        assert resp.status_code == 422

    def test_evaluation_result_not_found(self, auth_client, db):
        """Test 404 for non-existent screening result."""
        resp = auth_client.put(
            "/api/results/99999/evaluations",
            json={"question_category": "technical", "question_index": 0, "rating": "strong"},
        )
        assert resp.status_code == 404

    def test_evaluation_unauthenticated(self, client, db):
        """Test that unauthenticated requests are rejected (401 or 403 via CSRF)."""
        resp = client.put(
            "/api/results/1/evaluations",
            json={"question_category": "technical", "question_index": 0, "rating": "strong"},
        )
        # CSRF middleware may return 403 before auth returns 401
        assert resp.status_code in (401, 403)


# ─── Overall Assessment ───────────────────────────────────────────────────────

class TestOverallAssessment:
    """Test overall assessment endpoints."""

    def test_create_overall_assessment(self, auth_client, db):
        """Test creating an overall assessment."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)
        result = _create_test_result(db, tenant.id)

        resp = auth_client.put(
            f"/api/results/{result.id}/evaluations/overall",
            json={
                "overall_assessment": "Strong candidate with great potential",
                "recruiter_recommendation": "advance",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert "id" in data

    def test_update_overall_assessment(self, auth_client, db):
        """Test updating an existing overall assessment."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)
        result = _create_test_result(db, tenant.id)

        # Create
        auth_client.put(
            f"/api/results/{result.id}/evaluations/overall",
            json={
                "overall_assessment": "Initial assessment",
                "recruiter_recommendation": "hold",
            },
        )

        # Update
        resp = auth_client.put(
            f"/api/results/{result.id}/evaluations/overall",
            json={
                "overall_assessment": "Updated assessment — now advancing",
                "recruiter_recommendation": "advance",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "updated"

    def test_overall_assessment_tenant_isolation(self, auth_client, db):
        """Test that overall assessment respects tenant boundaries."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)

        other_tenant = Tenant(name="Other Corp OA", slug="other-corp-oa")
        db.add(other_tenant)
        db.commit()
        db.refresh(other_tenant)

        result = _create_test_result(db, other_tenant.id)

        resp = auth_client.put(
            f"/api/results/{result.id}/evaluations/overall",
            json={"overall_assessment": "Attempt", "recruiter_recommendation": "advance"},
        )
        assert resp.status_code == 403

    def test_overall_assessment_recommendation_validation(self, auth_client, db):
        """Test that invalid recruiter_recommendation values are rejected."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)
        result = _create_test_result(db, tenant.id)

        resp = auth_client.put(
            f"/api/results/{result.id}/evaluations/overall",
            json={"overall_assessment": "Test", "recruiter_recommendation": "maybe"},
        )
        assert resp.status_code == 422


# ─── Scorecard ────────────────────────────────────────────────────────────────

class TestScorecard:
    """Test scorecard generation."""

    def test_scorecard_empty_evaluations(self, auth_client, db):
        """Test scorecard with no evaluations returns zeroed dimensions."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)
        result = _create_test_result(db, tenant.id, analysis={
            "fit_score": 72,
            "final_recommendation": "Consider",
            "jd_analysis": {"role_title": "Senior Engineer"},
            "interview_questions": {
                "technical_questions": ["Q1", "Q2"],
                "behavioral_questions": ["Q3"],
                "culture_fit_questions": ["Q4", "Q5", "Q6"],
            },
        })

        resp = auth_client.get(f"/api/results/{result.id}/scorecard")
        assert resp.status_code == 200
        data = resp.json()

        assert data["candidate_name"] == "Unknown"
        assert data["role_title"] == "Senior Engineer"
        assert data["fit_score"] == 72
        assert data["recommendation"] == "Consider"
        assert data["evaluator_email"] == user.email
        assert data["overall_assessment"] is None
        assert data["recruiter_recommendation"] is None

        # Dimensions should show total questions but zero evaluations
        assert data["technical_summary"]["total_questions"] == 2
        assert data["technical_summary"]["evaluated_count"] == 0
        assert data["technical_summary"]["strong_count"] == 0

        assert data["behavioral_summary"]["total_questions"] == 1
        assert data["culture_fit_summary"]["total_questions"] == 3

    def test_scorecard_with_evaluations(self, auth_client, db):
        """Test scorecard correctly aggregates evaluation data."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)
        result = _create_test_result(db, tenant.id, analysis={
            "fit_score": 85,
            "final_recommendation": "Shortlist",
            "jd_analysis": {"role_title": "Tech Lead"},
            "interview_questions": {
                "technical_questions": ["Q1", "Q2"],
                "behavioral_questions": ["Q3"],
                "culture_fit_questions": [],
            },
        }, parsed={
            "contact_info": {"name": "Jane Smith"},
        })

        # Create evaluations
        auth_client.put(
            f"/api/results/{result.id}/evaluations",
            json={"question_category": "technical", "question_index": 0, "rating": "strong", "notes": "Deep knowledge"},
        )
        auth_client.put(
            f"/api/results/{result.id}/evaluations",
            json={"question_category": "technical", "question_index": 1, "rating": "adequate"},
        )
        auth_client.put(
            f"/api/results/{result.id}/evaluations",
            json={"question_category": "behavioral", "question_index": 0, "rating": "weak", "notes": "Vague response"},
        )

        resp = auth_client.get(f"/api/results/{result.id}/scorecard")
        assert resp.status_code == 200
        data = resp.json()

        assert data["candidate_name"] == "Jane Smith"
        assert data["role_title"] == "Tech Lead"

        # Technical: 2 total, 2 evaluated, 1 strong, 1 adequate, 0 weak
        ts = data["technical_summary"]
        assert ts["total_questions"] == 2
        assert ts["evaluated_count"] == 2
        assert ts["strong_count"] == 1
        assert ts["adequate_count"] == 1
        assert ts["weak_count"] == 0
        assert ts["key_notes"] == ["Deep knowledge"]

        # Behavioral: 1 total, 1 evaluated, 0 strong, 0 adequate, 1 weak
        bs = data["behavioral_summary"]
        assert bs["total_questions"] == 1
        assert bs["evaluated_count"] == 1
        assert bs["weak_count"] == 1

        # Strengths and concerns
        assert "Deep knowledge" in data["strengths_confirmed"]
        assert "Vague response" in data["concerns_identified"]

    def test_scorecard_includes_overall_assessment(self, auth_client, db):
        """Test scorecard includes overall assessment when present."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)
        result = _create_test_result(db, tenant.id, analysis={
            "jd_analysis": {"role_title": "PM"},
            "interview_questions": {},
        })

        # Create overall assessment
        auth_client.put(
            f"/api/results/{result.id}/evaluations/overall",
            json={
                "overall_assessment": "Great cultural fit",
                "recruiter_recommendation": "advance",
            },
        )

        resp = auth_client.get(f"/api/results/{result.id}/scorecard")
        assert resp.status_code == 200
        data = resp.json()

        assert data["overall_assessment"] == "Great cultural fit"
        assert data["recruiter_recommendation"] == "advance"

    def test_scorecard_tenant_isolation(self, auth_client, db):
        """Test scorecard respects tenant boundaries."""
        tenant, user = _get_auth_tenant_and_user(db, auth_client)

        other_tenant = Tenant(name="Other Corp SC", slug="other-corp-sc")
        db.add(other_tenant)
        db.commit()
        db.refresh(other_tenant)

        result = _create_test_result(db, other_tenant.id)

        resp = auth_client.get(f"/api/results/{result.id}/scorecard")
        assert resp.status_code == 403

    def test_scorecard_result_not_found(self, auth_client, db):
        """Test 404 for non-existent screening result."""
        resp = auth_client.get("/api/results/99999/scorecard")
        assert resp.status_code == 404
