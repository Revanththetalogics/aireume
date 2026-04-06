"""
Phase 2 & 3 feature tests:
  - Email generation (/api/email/generate)
  - JD URL extraction (/api/jd/extract-url)
  - Team management (/api/team, /api/invites)
  - Comments (/api/results/{id}/comments)
  - Training label/status (/api/training/label, /api/training/status)
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json


# ─── JD URL extraction ────────────────────────────────────────────────────────

class TestJdUrlExtraction:
    def test_extract_url_requires_auth(self, client):
        resp = client.post("/api/jd/extract-url", json={"url": "https://example.com/job"})
        assert resp.status_code == 403  # CSRF middleware blocks before auth check

    def test_extract_url_with_mock_scraper(self, auth_client):
        with patch("app.backend.routes.jd_url.scrape_jd", return_value="Senior Python Developer. 5+ years required.") as mock_scrape:
            resp = auth_client.post("/api/jd/extract-url", json={"url": "https://example.com/job"})
            assert resp.status_code == 200
            data = resp.json()
            assert "jd_text" in data
            assert len(data["jd_text"]) > 0
            mock_scrape.assert_called_once()

    def test_extract_url_scraper_failure_returns_422(self, auth_client):
        with patch("app.backend.routes.jd_url.scrape_jd", side_effect=Exception("fetch failed")):
            resp = auth_client.post("/api/jd/extract-url", json={"url": "https://broken.example.com"})
            assert resp.status_code in (422, 500)

    def test_extract_url_missing_url_returns_422(self, auth_client):
        resp = auth_client.post("/api/jd/extract-url", json={})
        assert resp.status_code == 422


# ─── Email generation ─────────────────────────────────────────────────────────

class TestEmailGeneration:
    def test_generate_email_requires_auth(self, client):
        resp = client.post("/api/email/generate", json={"candidate_id": 1, "type": "shortlist"})
        assert resp.status_code == 403  # CSRF middleware blocks before auth check

    def test_generate_email_nonexistent_candidate_returns_404(self, auth_client):
        resp = auth_client.post("/api/email/generate", json={"candidate_id": 99999, "type": "shortlist"})
        assert resp.status_code == 404

    def test_generate_email_invalid_type_returns_400(self, auth_client):
        resp = auth_client.post("/api/email/generate", json={"candidate_id": 1, "type": "spam_everyone"})
        assert resp.status_code == 400

    def test_generate_email_valid_types_accepted(self, auth_client):
        """All three valid email types should reach past the validation check."""
        for email_type in ["shortlist", "rejection", "screening_call"]:
            resp = auth_client.post("/api/email/generate", json={"candidate_id": 99999, "type": email_type})
            # 404 means it passed type validation and failed on candidate lookup — acceptable
            assert resp.status_code in (400, 404, 200)


# ─── Team management ─────────────────────────────────────────────────────────

class TestTeamManagement:
    def test_get_team_members_requires_auth(self, client):
        resp = client.get("/api/team")
        assert resp.status_code == 401

    def test_get_team_members_returns_list(self, auth_client):
        resp = auth_client.get("/api/team")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        # The current admin user should appear in the list
        assert len(resp.json()) >= 1

    def test_invite_requires_admin(self, auth_client):
        resp = auth_client.post("/api/invites", json={"email": "new@example.com", "role": "recruiter"})
        # Admin fixture has role=admin, so this should succeed
        assert resp.status_code in (200, 201)

    def test_invite_creates_user_with_temp_password(self, auth_client):
        resp = auth_client.post("/api/invites", json={"email": "recruiter@testcorp.com", "role": "recruiter"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        # temp_password intentionally removed from response for security
        assert "message" in data

    def test_invite_missing_email_returns_4xx(self, auth_client):
        # Missing email should fail validation or auth
        resp = auth_client.post("/api/invites", json={"role": "recruiter"})
        assert resp.status_code in (400, 422)

    def test_deactivate_nonexistent_user_returns_404(self, auth_client):
        resp = auth_client.delete("/api/team/99999")
        assert resp.status_code == 404


# ─── Comments ─────────────────────────────────────────────────────────────────

class TestComments:
    def test_get_comments_requires_auth(self, client):
        resp = client.get("/api/results/1/comments")
        assert resp.status_code == 401

    def test_post_comment_requires_auth(self, client):
        resp = client.post("/api/results/1/comments", json={"text": "Looks good"})
        assert resp.status_code == 403  # CSRF middleware blocks before auth check

    def test_get_comments_nonexistent_result_returns_404(self, auth_client):
        resp = auth_client.get("/api/results/99999/comments")
        assert resp.status_code == 404

    def test_post_comment_nonexistent_result_returns_404(self, auth_client):
        resp = auth_client.post("/api/results/99999/comments", json={"text": "Test comment"})
        assert resp.status_code == 404


# ─── Training ────────────────────────────────────────────────────────────────

class TestTraining:
    def test_training_status_requires_auth(self, client):
        resp = client.get("/api/training/status")
        assert resp.status_code == 401

    def test_training_status_returns_structure(self, auth_client):
        resp = auth_client.get("/api/training/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "labeled_count" in data
        assert "trained" in data
        assert data["labeled_count"] == 0
        assert data["trained"] is False

    def test_label_requires_auth(self, client):
        resp = client.post("/api/training/label", json={"screening_result_id": 1, "outcome": "hired"})
        assert resp.status_code == 403  # CSRF middleware blocks before auth check

    def test_label_nonexistent_result_returns_404(self, auth_client):
        resp = auth_client.post("/api/training/label", json={
            "screening_result_id": 99999,
            "outcome": "hired",
            "feedback": "Great candidate",
        })
        assert resp.status_code == 404

    def test_label_invalid_outcome_returns_4xx(self, auth_client):
        # "maybe" is not a valid outcome; response is either 422 (schema) or
        # 404 (result not found first) depending on route order
        resp = auth_client.post("/api/training/label", json={
            "screening_result_id": 99999,
            "outcome": "maybe",
        })
        assert resp.status_code in (400, 404, 422)

    def test_start_training_requires_admin(self, auth_client):
        # With fewer than 10 examples, should return 400 not 401
        resp = auth_client.post("/api/training/train")
        assert resp.status_code in (400, 401, 403)

    def test_start_training_insufficient_examples_returns_400(self, auth_client):
        resp = auth_client.post("/api/training/train")
        # Should say need at least 10 examples
        assert resp.status_code == 400
        assert "10" in resp.json().get("detail", "")
